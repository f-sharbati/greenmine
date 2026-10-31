"""Versioned password KDF; retain verification of the previous scrypt format."""
import hashlib
import hmac

ITERATIONS=600_000

def hash_password(password,salt):
    value=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),bytes.fromhex(salt),ITERATIONS,dklen=32).hex()
    return f'pbkdf2_sha256${ITERATIONS}${value}'

def verify_password(password,salt,stored):
    try:
        if stored.startswith('pbkdf2_sha256$'):
            _,count,value=stored.split('$')
            rounds=int(count)
            if not 600_000<=rounds<=2_000_000:return False
            computed=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),bytes.fromhex(salt),rounds,dklen=32).hex()
            return hmac.compare_digest(computed,value)
        if len(stored)!=128:return False
        computed=hashlib.scrypt(password.encode('utf-8'),salt=bytes.fromhex(salt),n=16384,r=8,p=1,dklen=64).hex()
        return hmac.compare_digest(computed,stored)
    except (ValueError,TypeError):return False

def needs_upgrade(stored):return not stored.startswith(f'pbkdf2_sha256${ITERATIONS}$')
