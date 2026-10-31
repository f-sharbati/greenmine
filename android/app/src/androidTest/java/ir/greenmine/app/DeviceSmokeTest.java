package ir.greenmine.app;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.graphics.Bitmap;
import android.os.Bundle;
import java.io.File;
import java.io.FileOutputStream;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/** Runs inside our app on a real device. No emulator or third-party test dependency. */
public class DeviceSmokeTest extends Instrumentation {
    private MainActivity activity;
    private boolean authUi=true;
    @Override public void onCreate(Bundle args){super.onCreate(args);authUi=args==null||!"false".equals(args.getString("authUi"));start();}
    @Override public void onStart(){
        Bundle result=new Bundle();
        try {
            activity=(MainActivity)startActivitySync(new Intent(getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            await("document.querySelector('.header')!==null",30);
            require("location.origin==="+org.json.JSONObject.quote(BuildConfig.SERVER_URL),"Expected backend origin");
            if(authUi){
                await("document.querySelector('.auth-card')!==null||document.querySelector('.profile-button')!==null",60);
                require("document.querySelector('.auth-card')!==null","Auth form is visible; existing signed-in sessions are not modified");
                if(js("document.documentElement.lang").equals("\"en\""))click(".language");
                require("document.querySelector('input[name=password]')!==null","Login password field is present");
                require("document.querySelector('input[name=code]')===null","No premature OTP field before password check");
                click(".auth-links .text-link");await("document.querySelector('.auth-captcha img')!==null",15);
                require("document.querySelector('input[name=password_confirmation]')!==null","Sign-up confirms password");
                require("document.querySelector('input[name=captcha]')!==null","Registration has server CAPTCHA");
                require("document.querySelector('.auth-captcha img').naturalWidth===240","CAPTCHA image loaded");
                require("document.documentElement.scrollWidth<=innerWidth+1","Persian sign-up fits the screen");capture("auth-registration-fa.png");
                click(".language");require("document.documentElement.scrollWidth<=innerWidth+1","English sign-up fits the screen");capture("auth-registration-en.png");
                click(".auth-links .text-link");await("document.querySelector('input[name=password_confirmation]')===null",10);
                capture("auth-login.png");
                result.putString("stream","PASS: login and registration UI, sign-up CAPTCHA, password confirmation, FA/EN containment. No account was created and no email was sent. OTP protocol is covered by backend tests.\n");
                finish(Activity.RESULT_OK,result);return;
            }
            if(BuildConfig.SERVER_URL.startsWith("https:")){
                await("document.querySelector('.auth-card')!==null||document.querySelector('.profile-button')!==null",60);
                require("document.querySelector('.auth-card input[type=password]')!==null||document.querySelector('.profile-button')!==null","Hosted authentication loaded");
                capture("android-hosted-auth.png");
                result.putString("stream","PASS: HTTPS backend and authentication UI loaded on the physical phone. No production account was created or modified.\n");
                finish(Activity.RESULT_OK,result);return;
            }
            runOnMainSync(()->activity.testWebView().loadUrl(BuildConfig.SERVER_URL+"/"));
            await("document.querySelector('.hero-impact')!==null",30);Thread.sleep(1200);
            if(js("document.documentElement.lang").equals("\"en\""))click(".language");
            runOnMainSync(()->activity.testWebView().getSettings().setUseWideViewPort(true));
            for(int width:new int[]{320,360,390,430,768}){
                js("document.querySelector('meta[name=viewport]').content='width="+width+"';true");Thread.sleep(600);
                require("document.documentElement.scrollWidth<=innerWidth+1","Landing fits width "+width);
                require("(()=>{const r=document.querySelector('.header-actions>a.button').getBoundingClientRect();return r.left>=-1 && r.right<=innerWidth+1})()","Dashboard CTA stays in viewport at "+width);
                require("(()=>{const a=document.querySelector('.hero-copy').getBoundingClientRect(),b=document.querySelector('.hero-impact').getBoundingClientRect();return b.top>=a.bottom-1})()","Hero card does not overlap copy at "+width);
            }
            js("document.querySelector('meta[name=viewport]').content='width=device-width, initial-scale=1';true");
            runOnMainSync(()->activity.testWebView().getSettings().setUseWideViewPort(false));
            capture("landing-fa-fixed.png");click(".language");
            require("document.documentElement.scrollWidth<=innerWidth+1","English landing fits");capture("landing-en-fixed.png");
            click(".menu-button");require("getComputedStyle(document.querySelector('.main-nav')).display==='flex'","Hamburger opens visible menu");click(".menu-scrim");
            js("window._frames=[];window._frameEnd=performance.now()+1800;window._lastFrame=0;requestAnimationFrame(function sample(t){if(window._lastFrame)window._frames.push(t-window._lastFrame);window._lastFrame=t;if(t<window._frameEnd)requestAnimationFrame(sample)});true");
            click(".theme-toggle");await("!document.querySelector('.theme-toggle').disabled",10);capture("landing-theme-fixed.png");
            require("document.querySelector('.theme-transition-layer')===null","Theme uses a mask, no covering color layer");
            result.putString("frame_timing",js("JSON.stringify({samples:window._frames.length,p95ms:[...window._frames].sort((a,b)=>a-b)[Math.floor(window._frames.length*.95)]})"));
            js("window._testEmail='device-'+Date.now()+'@example.org';window._testPassword=crypto.randomUUID();window._authDone=false;fetch('/api/auth',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'register',email:window._testEmail,password:window._testPassword})}).then(r=>r.json()).then(p=>{window._authDone=!!p.user});true");
            await("window._authDone===true",20);
            js("window._seedDone=false;(async()=>{const post=async data=>{const r=await fetch('/api/engine',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(!r.ok)throw Error('seed');return r.json()};await post({action:'settings',plant:{name:'Device test plant',capacity_dc:14,capacity_ac:14,location_mode:'gps',latitude:35.7,longitude:51.4,tilt:30,azimuth:180,performance_ratio:.8},tariff:25000});for(const filename of ['202608.CSV','202609.CSV'])await post({action:'import',filename,csv:await(await fetch('/samples/'+filename)).text()});window._seedDone=true})().catch(()=>{window._seedDone=false});true");
            await("window._seedDone===true",30);
            runOnMainSync(()->activity.testWebView().loadUrl(BuildConfig.SERVER_URL+"/dashboard"));
            await("document.querySelector('.overview-metrics')!==null",30);
            await("document.querySelector('.workspace-actions button:disabled')===null",30);
            require("document.querySelector('.profile-button')!==null","Session cookie survives navigation");
            require("getComputedStyle(document.querySelector('.overview-metrics')).gridTemplateColumns.split(' ').length===1","Mobile single-column dashboard");
            require("document.documentElement.scrollWidth<=innerWidth+1","Authenticated dashboard fits phone");
            click("[role=tab][id$=trigger-readings]");await("document.querySelectorAll('tbody tr').length===61",15);
            runOnMainSync(()->activity.testWebView().reload());await("document.querySelector('.overview-metrics')!==null",30);
            click("[role=tab][id$=trigger-readings]");await("document.querySelectorAll('tbody tr').length===61",15);
            require("document.querySelector('.profile-button')!==null","Session and saved CSV survive reload");
            click("[role=tab][id$=trigger-overview]");await("document.querySelector('.overview-metrics')!==null",15);
            require("document.querySelector('.overview-metrics').getBoundingClientRect().top>=document.querySelector('.plant-scene').getBoundingClientRect().bottom+8","Mobile solar scene and cards have a visible gap");
            if(js("document.documentElement.lang").equals("\"en\""))click(".language");
            capture("android-authenticated.png");
            click(".profile-button");require("document.querySelector('.account-menu')!==null && getComputedStyle(document.querySelector('.main-nav')).display==='flex'","Profile opens account menu");
            require("document.querySelector('.account-identity').getBoundingClientRect().right<=innerWidth+1","Account email stays in viewport");
            require("document.querySelector('.account-logout').textContent.trim()===String.fromCharCode(1582,1585,1608,1580)","Correct Persian sign-out label");capture("profile-menu.png");click(".menu-scrim");
            if(js("document.documentElement.lang").equals("\"en\""))click(".language");
            require("document.querySelector('.workspace-actions .button.outline').textContent.includes('PDF')","PDF clearly named on export button");
            click(".workspace-actions .button.outline");await("document.querySelector('.export-options')!==null",10);
            require("document.querySelector('.export-options').innerText.includes('PDF')&&document.querySelector('.export-options').innerText.includes('CSV')","CSV and PDF formats available");
            click(".export-options .button.dark");Thread.sleep(1800);capture("android-pdf-preview.png");
            android.view.accessibility.AccessibilityNodeInfo printRoot=getUiAutomation().getRootInActiveWindow();
            if(printRoot==null||printRoot.getPackageName()==null||!printRoot.getPackageName().toString().contains("printspooler"))throw new AssertionError("Android PDF print preview did not open");
            sendKeyDownUpSync(android.view.KeyEvent.KEYCODE_BACK);Thread.sleep(600);
            runOnMainSync(()->{activity.testWebView().getSettings().setUseWideViewPort(true);activity.testWebView().getSettings().setLoadWithOverviewMode(true);});
            js("document.querySelector('meta[name=viewport]').content='width=1280';true");Thread.sleep(1200);
            require("getComputedStyle(document.querySelector('.overview-metrics')).gridTemplateColumns.split(' ').length===3","Desktop grid preserved");
            require("getComputedStyle(document.querySelector('.overview-grid')).backgroundImage.includes('solar-minimal-wide')","Wide minimal solar image fills overview");
            js("document.querySelector('meta[name=viewport]').content='width=device-width, initial-scale=1';true");
            runOnMainSync(()->{activity.testWebView().getSettings().setUseWideViewPort(false);activity.testWebView().getSettings().setLoadWithOverviewMode(false);});
            click("[role=tab][id$=trigger-forecast]");await("document.querySelector('.forecast-header')!==null",15);
            click(".forecast-header button");await("document.querySelector('.forecast-stats')!==null||document.querySelector('.forecast-error')!==null",65);
            require("document.querySelector('.forecast-stats')!==null","Live forecast returned results");capture("forecast-live.png");
            require("!document.querySelector('.forecast-header h2').textContent.includes(String.fromCharCode(1644))","Persian year has no thousands separator");
            require("!document.querySelector('.forecast-header h2').textContent.includes(String.fromCharCode(1548))","Year is ungrouped");
            require("document.querySelector('.forecast-stats').textContent.includes(String.fromCharCode(1548))","Persian thousands use requested comma");
            click(".forecast-window button:nth-child(2)");await("!document.querySelector('.forecast-header button').disabled",65);
            require("!document.querySelector('.forecast-header h2').textContent.includes('2026')","Persian rolling dates use Persian calendar");
            click(".setting-button");await("document.querySelector('.plant-location')!==null",10);
            require("[...document.querySelectorAll('.plant-location input[type=number]')].length===2","Required coordinates are visible outside optional settings");
            click(".dialog-content .full-button");await("document.querySelector('.plant-location')===null",15);
            await("document.querySelector('.forecast-stats')!==null && !document.querySelector('.forecast-header button').disabled",65);
            require("document.querySelector('.forecast-error')===null","Saving settings continues to a successful forecast");
            click(".setting-button");await("document.querySelector('[data-pilot-preset]')!==null",10);
            click("[data-pilot-preset]");
            require("[...document.querySelectorAll('.dialog-content input')].every(e=>e.checkValidity())","Pilot settings satisfy form constraints");
            click(".dialog-content .full-button");await("document.querySelector('.plant-location')===null",20);
            await("document.querySelector('.validation-panel .validation-stats')!==null && !document.querySelector('.forecast-header button').disabled",65);
            require("document.querySelector('.validation-panel').textContent.includes('1.61')||document.querySelector('.validation-panel').textContent.includes(String.fromCharCode(1777)+'.'+String.fromCharCode(1782,1777))","Measured monthly error displayed");
            require("document.documentElement.scrollWidth<=innerWidth+1","Validation panel fits mobile");
            js("document.querySelector('.validation-panel').scrollIntoView({block:'start'});true");capture("prediction-validation-fa.png");
            click(".profile-button");click(".account-logout");await("document.querySelector('.auth-card')!==null",15);
            result.putString("stream","PASS: visible PDF export, Persian sign-out text, contained landing CTA, mobile card separation, wide solar image, localized dates and numbers, live forecast, save-and-forecast form, FA/EN landing, 320/360/390/430/768px layouts, non-overlapping hero, theme, authenticated backend, persisted CSV and sessions, logout, mobile/desktop dashboard layouts. Local disposable accounts only.\n");
            result.putString("stream",result.getString("stream")+"Theme rAF sample (development WebView): "+result.getString("frame_timing")+"\n");
            finish(Activity.RESULT_OK,result);
        }catch(Throwable error){result.putString("stream","FAIL: "+error.toString()+"\n");finish(Activity.RESULT_CANCELED,result);}
    }
    private String js(String script) throws Exception {
        CountDownLatch latch=new CountDownLatch(1);AtomicReference<String> value=new AtomicReference<>();
        runOnMainSync(()->activity.testWebView().evaluateJavascript(script,r->{value.set(r);latch.countDown();}));
        if(!latch.await(10,TimeUnit.SECONDS))throw new AssertionError("JavaScript callback timed out");
        return value.get();
    }
    private void require(String predicate,String label)throws Exception{if(!"true".equals(js(predicate)))throw new AssertionError(label);}
    private void await(String predicate,int seconds)throws Exception{long until=System.currentTimeMillis()+seconds*1000L;while(System.currentTimeMillis()<until){if("true".equals(js(predicate)))return;Thread.sleep(250);}throw new AssertionError("Timed out: "+predicate);}
    private void click(String selector)throws Exception{require("(()=>{const el=document.querySelector("+org.json.JSONObject.quote(selector)+");if(!el)return false;if(el.getAttribute('role')==='tab')el.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,button:0}));el.click();return true;})()","Click "+selector);Thread.sleep(400);}
    private void capture(String name)throws Exception{Thread.sleep(800);Bitmap bitmap=getUiAutomation().takeScreenshot();try(FileOutputStream out=new FileOutputStream(new File(getTargetContext().getFilesDir(),name))){bitmap.compress(Bitmap.CompressFormat.PNG,100,out);}bitmap.recycle();}
    private void tap(String selector)throws Exception{
        String raw=js("(()=>{const r=document.querySelector("+org.json.JSONObject.quote(selector)+").getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]})()");
        org.json.JSONArray xy=new org.json.JSONArray(raw);int[] origin=new int[2];float[] scale=new float[1];
        runOnMainSync(()->{activity.testWebView().getLocationOnScreen(origin);scale[0]=activity.testWebView().getScale();});
        float x=origin[0]+(float)xy.getDouble(0)*scale[0],y=origin[1]+(float)xy.getDouble(1)*scale[0];long now=android.os.SystemClock.uptimeMillis();
        android.view.MotionEvent down=android.view.MotionEvent.obtain(now,now,android.view.MotionEvent.ACTION_DOWN,x,y,0);
        android.view.MotionEvent up=android.view.MotionEvent.obtain(now,now+70,android.view.MotionEvent.ACTION_UP,x,y,0);
        sendPointerSync(down);sendPointerSync(up);down.recycle();up.recycle();
    }
    private void awaitPicker()throws Exception{
        long until=System.currentTimeMillis()+10000;
        while(System.currentTimeMillis()<until){android.view.accessibility.AccessibilityNodeInfo root=getUiAutomation().getRootInActiveWindow();if(root!=null&&root.getPackageName()!=null&&root.getPackageName().toString().contains("documentsui"))return;Thread.sleep(250);}
        throw new AssertionError("Android document picker did not open");
    }
}
