# ==============================================
# 🧮 Simple Calculator in Python
# Supports: Addition, Subtraction, Multiplication, Division, Power
# ==============================================

def add(x, y):
    """Return the sum of x and y"""
    return x + y

def subtract(x, y):
    """Return the difference of x and y"""
    return x - y

def multiply(x, y):
    """Return the product of x and y"""
    return x * y

def divide(x, y):
    """Return the division of x by y"""
    if y == 0:
        return "Error: Division by zero!"
    return x / y

def power(x, y):
    """Return x raised to the power y"""
    return x ** y

def calculator():
    print("\n==============================")
    print(" 🧮  Simple Python Calculator")
    print("==============================")
    print("Select operation:")
    print("1. Add")
    print("2. Subtract")
    print("3. Multiply")
    print("4. Divide")
    print("5. Power")
    print("6. Exit")

    while True:
        choice = input("\nEnter choice (1/2/3/4/5/6): ")

        if choice == '6':
            print("Exiting calculator. Goodbye!")
            break

        if choice in ['1', '2', '3', '4', '5']:
            try:
                num1 = float(input("Enter first number: "))
                num2 = float(input("Enter second number: "))
            except ValueError:
                print("⚠️  Invalid input. Please enter numbers only.")
                continue

            if choice == '1':
                print(f"Result: {add(num1, num2)}")
            elif choice == '2':
                print(f"Result: {subtract(num1, num2)}")
            elif choice == '3':
                print(f"Result: {multiply(num1, num2)}")
            elif choice == '4':
                print(f"Result: {divide(num1, num2)}")
            elif choice == '5':
                print(f"Result: {power(num1, num2)}")
        else:
            print("⚠️ Invalid choice, please select from 1–6.")

if __name__ == "__main__":
    calculator()
