"""Self-hosted image CAPTCHA: expiring, browser-bound and single use."""
import base64,hashlib,hmac,secrets,struct,time,zlib
from recovery import key

# Raster glyphs keep the solution out of image markup and accessibility text.
GLYPHS={
 '2':['11110','00001','00001','01110','10000','10000','11111'],
 '3':['11110','00001','00001','01110','00001','00001','11110'],
 '4':['10010','10010','10010','11111','00010','00010','00010'],
 '5':['11111','10000','10000','11110','00001','00001','11110'],
 '6':['01111','10000','10000','11110','10001','10001','01110'],
 '7':['11111','00001','00010','00100','01000','01000','01000'],
 '8':['01110','10001','10001','01110','10001','10001','01110'],
 '9':['01110','10001','10001','01111','00001','00001','11110']}

def normalized(value):return str(value).strip().translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩','01234567890123456789'))
def answer_hash(challenge,answer,binding):return hmac.new(key(),f'captcha:{challenge}:{binding}:{answer}'.encode(),hashlib.sha256).hexdigest()

def image(answer):
    width,height=240,70;pixels=bytearray([231,240,247]*(width*height))
    def dot(x,y,color):
        if 0<=x<width and 0<=y<height:pixels[(y*width+x)*3:(y*width+x)*3+3]=bytes(color)
    for i,char in enumerate(answer):
        ox=12+i*37;oy=12+secrets.randbelow(12)
        for y,row in enumerate(GLYPHS[char]):
            for x,v in enumerate(row):
                if v=='1':
                    for dy in range(5):
                        for dx in range(5):dot(ox+x*5+dx,oy+y*5+dy,(28,66+i*7,91))
    for _ in range(350):dot(secrets.randbelow(width),secrets.randbelow(height),(89,137,151))
    def chunk(tag,data):return struct.pack('!I',len(data))+tag+data+struct.pack('!I',zlib.crc32(tag+data)&0xffffffff)
    raw=b''.join(b'\0'+pixels[y*width*3:(y+1)*width*3] for y in range(height))
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
    return 'data:image/png;base64,'+base64.b64encode(png).decode()

def create(db,binding,client,api):
    api['rate'](db,'captcha-ip:'+api['digest'](client),40)
    challenge=secrets.token_hex(24);answer=''.join(secrets.choice(tuple(GLYPHS)) for _ in range(6));now=int(time.time())
    with db:
        db.execute('DELETE FROM captcha_challenges WHERE expires_at<=? OR binding_hash=?',(now,api['digest'](binding)))
        db.execute('INSERT INTO captcha_challenges VALUES (?,?,?,?)',(challenge,api['digest'](binding),answer_hash(challenge,answer,binding),now+300))
    return {'captcha_id':challenge,'image':image(answer),'expires_in':300}

def consume(db,data,binding,api):
    cid=data.get('captcha_id');answer=normalized(data.get('captcha_answer',''))
    valid=False
    if isinstance(cid,str) and len(cid)==48:
        with db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM captcha_challenges WHERE id=?',(cid,)).fetchone()
            if row and row['binding_hash']==api['digest'](binding):
                db.execute('DELETE FROM captcha_challenges WHERE id=?',(cid,))
                valid=row['expires_at']>int(time.time()) and hmac.compare_digest(row['answer_hash'],answer_hash(cid,answer,binding))
    if not valid:raise api['error']('CAPTCHA_INVALID',422)
