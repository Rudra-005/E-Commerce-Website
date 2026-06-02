import random

secret_number = random.randint(1, 10)
attempts = 5

print("Guess the number between 1 and 10")
print(f"You have {attempts} attempts")

for i in range(attempts):
    guess = int(input("Enter your guess: "))

    if guess == secret_number:
        print("Congratulations! You guessed the number.")
        break
    elif guess < secret_number:
        print("The number is greater than your guess.")
    else:
        print("The number is less than your guess.")

    print(f"Attempts left: {attempts - i - 1}")

else:
    print(f"Game Over! The number was {secret_number}")