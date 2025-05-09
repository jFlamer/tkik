from grammar.OOPsyBaseVisitor import OOPsyBaseVisitor


class ClassDef:
    def __init__(self, name, superclass=None):
        self.name = name
        self.superclass = superclass
        self.attributes = {}
        self.methods = {}

    def get_attr(self, name):
        if name in self.attributes:
            return None
        elif self.superclass:
            return self.superclass.get_attr(name)
        else:
            raise Exception(f"Atrybut '{name}' nie istnieje w klasie '{self.name}' ani w jej nadklasie")


class Instance:
    def __init__(self, class_def):
        self.class_def = class_def
        self.fields = {}

    def get_attr(self, name):
        if name in self.fields:
            return self.fields[name]
        elif name in self.class_def.attributes:
            return None  # domyślna wartość
        elif self.class_def.superclass:
            return self.class_def.superclass.get_attr(name)
        else:
            raise Exception(f"Brak atrybutu '{name}' w obiekcie '{self.class_def.name}'")

    def set_attr(self, name, value):
        if name in self.class_def.attributes or self.class_def.superclass:
            self.fields[name] = value
        else:
            raise Exception(f"Próba ustawienia nieistniejącego atrybutu '{name}'")

class Interpreter(OOPsyBaseVisitor):
    def __init__(self):
        super().__init__()
        self.classes = {}
        self.variables = {}
        self.current_instance = None

    def visitProgram(self, ctx):
        for child in ctx.classDecl():
            self.visit(child)
        self.visit(ctx.mainMethod())

    def visitClassDecl(self, ctx):
        name = ctx.IDENTIFIER(0).getText()
        superclass = None
        if ctx.INHERITS_KEYWORD():
            superclass_name = ctx.IDENTIFIER(1).getText()
            superclass = self.classes.get(superclass_name)
            if superclass is None:
                raise Exception(f"Brak klasy bazowej '{superclass_name}'")
        class_def = ClassDef(name, superclass)
        for element in ctx.classElement():
            if element.attributeDecl():
                attr_name = element.attributeDecl().IDENTIFIER().getText()
                class_def.attributes[attr_name] = None
            elif element.methodDecl():
                method_name = element.methodDecl().IDENTIFIER().getText()
                class_def.methods[method_name] = element.methodDecl()
        self.classes[name] = class_def

    def visitMainMethod(self, ctx):
        self.visit(ctx.block())

    def visitBlock(self, ctx):
        for stmt in ctx.statement():
            self.visit(stmt)

    def visitCreateStatement(self, ctx):
        var_name = ctx.IDENTIFIER(0).getText()
        class_name = ctx.IDENTIFIER(1).getText()
        class_def = self.classes.get(class_name)
        if not class_def:
            raise Exception(f"Nieznana klasa '{class_name}'")
        instance = Instance(class_def)

        if ctx.argumentList():
            args = [self.visit(arg) for arg in ctx.argumentList().valueExpression()]
            self.set_constructor_attributes(instance, args)

        self.variables[var_name] = instance

    def visitAssignment(self, ctx):
        target = ctx.getChild(0)
        value = self.visit(ctx.valueExpression())

        if target.getChildCount() == 1:  # zwykła zmienna
            var_name = target.getText()
            if var_name in self.variables:
                self.variables[var_name] = value
            else:
                raise Exception(f"Nieznana zmienna '{var_name}'")
        else:  # przypisanie do pola obiektu
            obj_name = target.getChild(0).getText()
            attr_name = target.getChild(2).getText()

            if obj_name == "self":
                if self.current_instance is None:
                    raise Exception("Użycie 'self' poza metodą")
                self.current_instance.set_attr(attr_name, value)
            else:
                obj = self.variables.get(obj_name)
                if not obj:
                    raise Exception(f"Nieznany obiekt '{obj_name}'")
                obj.set_attr(attr_name, value)

    def visitPrintStatement(self, ctx):
        value = self.visit(ctx.valueExpression())
        print(value)

    def visitIfStatement(self, ctx):
        condition = self.visit(ctx.logicalExpression())
        if condition:
            self.visit(ctx.block(0))
        elif ctx.ELSE_KEYWORD():
            self.visit(ctx.block(1))

    def visitLoopStatement(self, ctx):
        while True:
            self.visit(ctx.block())
            if self.visit(ctx.logicalExpression()):
                break

    # def visitReturnStatement(self, ctx):
    #     raise Exception("Instrukcja 'return' obsługiwana tylko w pełnym wykonaniu funkcji (do zaimplementowania)")
    def visitReturnStatement(self, ctx):
        return

    def visitMethodCall(self, ctx):
        obj_name = ctx.IDENTIFIER(0).getText()
        method_name = ctx.IDENTIFIER(1).getText()
        obj = self.variables.get(obj_name)
        if not obj:
            raise Exception(f"Nieznany obiekt '{obj_name}'")
        method = obj.class_def.methods.get(method_name)
        if not method and obj.class_def.superclass:
            method = obj.class_def.superclass.methods.get(method_name)
        if not method:
            raise Exception(f"Obiekt '{obj_name}' nie posiada metody '{method_name}()'")
        saved_instance = self.current_instance
        self.current_instance = obj
        self.visit(method.block())
        self.current_instance = saved_instance

    def visitMemberAccess(self, ctx):
        obj_name = ctx.getChild(0).getText()
        attr_name = ctx.getChild(2).getText()

        if obj_name == "self":
            if self.current_instance is None:
                raise Exception("Użycie 'self' poza metodą")
            return self.current_instance.get_attr(attr_name)

        obj = self.variables.get(obj_name)
        if not obj:
            raise Exception(f"Nieznany obiekt '{obj_name}'")
        return obj.get_attr(attr_name)

    def visitValueExpression(self, ctx):
        if ctx.INT_LITERAL():
            return int(ctx.INT_LITERAL().getText())
        if ctx.FLOAT_LITERAL():
            return float(ctx.FLOAT_LITERAL().getText())
        if ctx.STRING_LITERAL():
            return ctx.STRING_LITERAL().getText().strip('"')
        if ctx.CHAR_LITERAL():
            return ctx.CHAR_LITERAL().getText().strip("'")
        if ctx.BOOL_LITERAL_TRUE():
            return True
        if ctx.BOOL_LITERAL_FALSE():
            return False
        if ctx.IDENTIFIER():
            var_name = ctx.IDENTIFIER().getText()
            if var_name in self.variables:
                return self.variables[var_name]
            raise Exception(f"Nieznana zmienna '{var_name}'")
        if ctx.methodCall():
            return self.visit(ctx.methodCall())
        if ctx.memberAccess():
            return self.visit(ctx.memberAccess())
        if ctx.valueExpression(0) and ctx.valueExpression(1):
            left = self.visit(ctx.valueExpression(0))
            right = self.visit(ctx.valueExpression(1))
            op = ctx.getChild(1).getText()
            return self.evaluate_binary_operation(left, op, right)
        if ctx.LEFT_PARENTHESIS():
            return self.visit(ctx.valueExpression(0))

    def visitLogicalExpression(self, ctx):
        result = self.visit(ctx.logicalTerm(0))
        for i in range(1, len(ctx.logicalTerm())):
            result = result or self.visit(ctx.logicalTerm(i))
        return result

    def visitLogicalTerm(self, ctx):
        result = self.visit(ctx.logicalFactor(0))
        for i in range(1, len(ctx.logicalFactor())):
            result = result and self.visit(ctx.logicalFactor(i))
        return result

    def visitLogicalFactor(self, ctx):
        if ctx.valueExpression(1):
            left = self.visit(ctx.valueExpression(0))
            right = self.visit(ctx.valueExpression(1))
            op = ctx.getChild(1).getText()
            return self.evaluate_comparison(left, op, right)
        else:
            return self.visit(ctx.valueExpression(0))

    def evaluate_binary_operation(self, left, op, right):
        if op == '+':
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            return left + right
        if op == '-':
            return left - right
        if op == '*':
            return left * right
        if op == '/':
            return left / right
        if op == '%':
            return left % right
        raise Exception(f"Nieznany operator arytmetyczny '{op}'")

    def evaluate_comparison(self, left, op, right):
        if op == '==':
            return left == right
        if op == '!=':
            return left != right
        if op == '<':
            return left < right
        if op == '>':
            return left > right
        if op == '<=':
            return left <= right
        if op == '>=':
            return left >= right
        raise Exception(f"Nieznany operator porównania '{op}'")

    def set_constructor_attributes(self, instance, args):
        def collect_attributes(class_def):
            attrs = []
            if class_def.superclass:
                attrs.extend(collect_attributes(class_def.superclass))
            attrs.extend(list(class_def.attributes.keys()))
            return attrs

        attr_names = collect_attributes(instance.class_def)
        for i, value in enumerate(args):
            if i < len(attr_names):
                instance.set_attr(attr_names[i], value)
