from random import randint
import hashlib, base64

# FIXME hash can be reused
def generate(key):
    '''
    Generate a simple CAPTCHA.
    It is based on a simple math expression which stops the simplest of bots.
    '''
    # The parameters are chosen such that they are simple to solve on paper.
    a = randint(1, 10)
    b = randint(1, 10)
    c = randint(10, 20)
    return f'{a} * {b} + {c} = ', _hash_answer(key, str(a * b + c))

def verify(key, answer, hash):
    return _hash_answer(key, answer) == hash

def _hash_answer(key, answer):
    return base64.b64encode(hashlib.sha256((key + answer).encode('utf-8')).digest()).decode('ascii')
