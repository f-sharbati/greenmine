import smtplib

EMAIL = "mehrava.sharbati@gmail.com"
APP_PW = "qftphixezkxbrzmn".replace(" ", "").strip()

print("len =", len(APP_PW))   # 16

s = smtplib.SMTP("smtp.gmail.com", 587)
s.starttls()
s.login(EMAIL, APP_PW)
print("Login OK")
s.quit()
