"""
this is the example data that we will be working with
"""

class User:
    """User class representing a person with basic attributes."""
    def __init__(self, name: str, age: int, email: str):
        self.name = name
        self.age = age
        self.email = email

    def __repr__(self):
        return f"User(name={self.name!r}, age={self.age!r}, email={self.email!r})" 
    