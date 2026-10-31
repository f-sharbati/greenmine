"""Unit-test fixture only. No HTTP route or runtime authentication bypass."""
import secrets
from unittest.mock import patch
import service

def call_service(request):
    if request.get('op') not in ('register','login'):return service.main(request)
    messages=[];binding=secrets.token_hex(32)
    req={**request,'binding':binding,'data':dict(request.get('data',{}))}
    if req['op']=='register':req['data']['password_confirmation']=req['data'].get('password')
    with patch('auth_flow.available',return_value=True),patch('auth_flow.send_otp',side_effect=lambda email,code,purpose:messages.append(code)),patch('captcha.consume'):
        result=service.main(req)
        if result['stage']=='activation':
            service.main({'op':'auth_verify','binding':binding,'data':{'challenge_id':result['challenge_id'],'code':messages[-1]},'client':request.get('client','test')})
            result=service.main({**req,'op':'login'})
        return service.main({'op':'auth_verify','binding':binding,'data':{'challenge_id':result['challenge_id'],'code':messages[-1]},'client':request.get('client','test')})
