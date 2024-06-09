import secrets

def generate_secret_key():
    return secrets.token_hex(32)

# Generate and print a secret key
print(generate_secret_key())
