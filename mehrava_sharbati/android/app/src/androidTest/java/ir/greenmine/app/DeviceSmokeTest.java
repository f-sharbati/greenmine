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
    @Override public void onCreate(Bundle args){super.onCreate(args);start();}
    @Override public void onStart(){
        Bundle result=new Bundle();
        try {
            Intent intent=new Intent(getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            activity=(MainActivity)startActivitySync(intent);
            await("document.querySelector('.workspace')!==null",30);
            await("document.querySelector('.workspace-actions button:disabled')===null",60);

            if(js("document.documentElement.dataset.theme").equals("\"dark\"")){click(".theme-toggle");await("!document.querySelector('.theme-toggle').disabled",10);}
            if(js("document.documentElement.lang").equals("\"en\"")) click(".language");
            await("document.documentElement.dir==='rtl'",10);
            require("document.documentElement.scrollWidth<=innerWidth+1","No horizontal overflow in Persian");
            require("Array.from(document.querySelectorAll('.eyebrow,.metric-card p,.tab,.workspace-bottom')).every(el=>parseFloat(getComputedStyle(el).fontSize)>=12)","Small text at least 12px");
            capture("android-fa.png");
            click(".language");await("document.documentElement.lang==='en'&&document.documentElement.dir==='ltr'",10);
            require("document.documentElement.scrollWidth<=innerWidth+1","No horizontal overflow in English");
            capture("android-en.png");
            require("getComputedStyle(document.querySelector('.overview-metrics')).gridTemplateColumns.split(' ').length===1","One card per row");
            click(".theme-toggle");await("!document.querySelector('.theme-toggle').disabled",10);
            require("document.documentElement.dataset.theme==='dark'","Dark theme applied");
            require("localStorage.getItem('greenmine-theme')==='dark'","Theme saved");
            capture("android-dark.png");
            click(".theme-toggle");await("!document.querySelector('.theme-toggle').disabled",10);
            js("document.querySelector('.compass-card').scrollIntoView({block:'center'});true");Thread.sleep(2400);
            click(".compass-card .replay-button");
            require("(()=>{const e=document.querySelector('.compass-marker');return Math.abs(Math.hypot(+e.getAttribute('cx')-120,+e.getAttribute('cy')-120)-84)<.1})()","Compass marker follows circle during animation");
            Thread.sleep(2000);capture("android-compass.png");
            js("document.querySelector('.gauge-card').scrollIntoView({block:'center'});true");Thread.sleep(2400);
            click(".gauge-card .replay-button");
            require("(()=>{const e=document.querySelector('.gauge-marker');return Math.abs(Math.hypot(+e.getAttribute('cx')-130,+e.getAttribute('cy')-130)-100)<.1})()","Performance marker follows circle during animation");
            Thread.sleep(2000);capture("android-gauge.png");
            js("document.querySelector('.overview-metrics').scrollIntoView({block:'start'});true");capture("android-data.png");
            js("document.querySelector('.analytics-row').scrollIntoView({block:'start',behavior:'instant'});true");
            Thread.sleep(650);
            js("window._earlyBarHeight=document.querySelector('.chart-bar').getBoundingClientRect().height;true");
            Thread.sleep(1800);
            require("document.querySelector('.chart-bar').getBoundingClientRect().height>window._earlyBarHeight+2","Bars animate after entering viewport");
            capture("android-chart.png");
            require("document.documentElement.scrollWidth<=innerWidth+1","Chart fits phone width");
            js("scrollTo(0,0);true");
            click(".setting-button");await("document.querySelector('[role=dialog]')!==null",10);
            require("document.querySelector('[role=dialog] input')!==null","Settings form opens");
            click(".dialog-close");
            js("document.querySelector('[role=tab][id$=trigger-readings]').dispatchEvent(new MouseEvent('mousedown',{bubbles:true,button:0}));true");
            Thread.sleep(80);
            require("document.querySelector('[data-panel=overview][inert]')!==null","Outgoing cards retained for exit animation");
            await("document.querySelectorAll('tbody tr').length===61",10);
            click("[role=tab][id$=trigger-impact]");await("document.querySelector('.carbon-note')!==null",10);
            await("document.body.innerText.includes('259.39')||document.body.innerText.includes('259.4')",10);
            click("[role=tab][id$=trigger-overview]");
            js("scrollTo(0,0);true");Thread.sleep(500);
            tap(".workspace-actions .button.outline");
            awaitPicker();sendKeyDownUpSync(android.view.KeyEvent.KEYCODE_BACK);Thread.sleep(600);
            click(".workspace-actions .button.dark");await("document.querySelector('.upload-zone')!==null",10);
            tap(".upload-zone");awaitPicker();sendKeyDownUpSync(android.view.KeyEvent.KEYCODE_BACK);Thread.sleep(600);
            click(".dialog-close");
            click(".language");await("document.documentElement.dir==='rtl'",10);
            js("localStorage.setItem('greenmine-language','fa');true");
            runOnMainSync(()->{activity.testWebView().getSettings().setUseWideViewPort(true);activity.testWebView().getSettings().setLoadWithOverviewMode(true);});
            js("document.querySelector('meta[name=viewport]').content='width=1280';scrollTo(0,0);true");Thread.sleep(1600);
            require("innerWidth>=1024 && getComputedStyle(document.querySelector('.overview-grid')).display==='grid'","Desktop solar scene and instruments side by side");
            require("getComputedStyle(document.querySelector('.overview-metrics')).gridTemplateColumns.split(' ').length===3","Desktop three-column instrument grid");
            js("document.querySelector('.overview-grid').scrollIntoView({block:'start',behavior:'instant'});true");Thread.sleep(2600);capture("desktop-layout.png");
            js("document.querySelector('meta[name=viewport]').content='width=device-width, initial-scale=1';scrollTo(0,0);true");
            runOnMainSync(()->{activity.testWebView().getSettings().setUseWideViewPort(false);activity.testWebView().getSettings().setLoadWithOverviewMode(false);});
            result.putString("stream","PASS: desktop grid restored, viewport-triggered bar animations, single-column cards, circular gauge motion, retained exit animation, saved light/dark theme, production data, FA/EN directions, text sizing, overflow, settings, readings, impact and native CSV pickers on device.\n");
            finish(Activity.RESULT_OK,result);
        } catch(Throwable error){String detail="";try{detail=js("JSON.stringify({ready:document.readyState,lang:document.documentElement.lang,text:document.body.innerText.slice(0,1500)})");}catch(Exception ignored){}result.putString("stream","FAIL: "+error.toString()+"\n"+detail+"\n");finish(Activity.RESULT_CANCELED,result);}
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
