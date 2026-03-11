---
description: Code quality guidelines to be follow when writing production code
applyTo: 'app/**/*.py'
---

Follow clean code principles and classical design principles to ensure maintainability and readability of the codebase. This includes:

- Single Responsibility Principle: Each class should have only one reason to change.
- Open/Closed Principle: Software entities should be open for extension but closed for modification.
- Liskov Substitution Principle: Objects of a superclass should be replaceable with objects of a subclass without affecting the correctness of the program.
- Interface Segregation Principle: Clients should not be forced to depend on interfaces they do not use.
- Dependency Inversion Principle: High-level modules should not depend on low-level modules. Both should depend on abstractions.
- Keep functions small and focused on a single task.
- Use meaningful names for variables, functions, and classes to enhance readability.
- Avoid deep nesting of code to improve readability.
- Write unit tests to ensure code correctness and facilitate future refactoring.
- Use type hints to improve code clarity and catch potential bugs early.
- Avoid global state and mutable shared data to prevent unintended side effects.
- Use logging instead of print statements for better control over output and to facilitate debugging in production environments.
