MIN_PASSWORD_CHARACTERS = 8

# bcrypt only uses the first 72 bytes of a password. Reject longer passwords
# so users do not think extra characters are protecting their account.
MAX_BCRYPT_PASSWORD_BYTES = 72
