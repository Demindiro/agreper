import passlib.hash

def hash(password):
    return passlib.hash.argon2.hash(password)

def verify(password, hash):
    return passlib.hash.argon2.verify(password, hash)


