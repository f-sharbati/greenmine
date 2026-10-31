package ir.greenmine.app;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.*;
import android.widget.*;
import org.json.JSONObject;
import java.io.OutputStream;
import java.io.InputStream;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.HashMap;
import java.nio.charset.StandardCharsets;

/** Android shell for the same Next.js app; predictions stay in the original Python backend. */
public class MainActivity extends Activity {
    private static final int PICK_CSV = 20, SAVE_CSV = 21;
    private WebView web;
    private WebViewClient mainClient;
    private WebView reportWeb;
    private LinearLayout errorPanel;
    private ProgressBar progress;
    private ValueCallback<Uri[]> pendingFile;
    private String pendingCsv;
    private final Uri server = Uri.parse(BuildConfig.SERVER_URL);

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(226,233,242));
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets i = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout() | WindowInsets.Type.ime());
                v.setPadding(i.left, i.top, i.right, i.bottom);
            } else {
                v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            }
            return insets;
        });
        web = new WebView(this);
        root.addView(web, new FrameLayout.LayoutParams(-1,-1));
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setProgressTintList(android.content.res.ColorStateList.valueOf(Color.rgb(241,91,60)));
        root.addView(progress,new FrameLayout.LayoutParams(-1,dp(3),Gravity.TOP));
        errorPanel = new LinearLayout(this);
        errorPanel.setOrientation(LinearLayout.VERTICAL);
        errorPanel.setGravity(Gravity.CENTER);
        errorPanel.setPadding(dp(28),dp(28),dp(28),dp(28));
        errorPanel.setBackgroundColor(Color.rgb(226,233,242));
        TextView title = new TextView(this);
        title.setText("GreenMine\nگرین‌ماین"); title.setTextSize(30); title.setGravity(Gravity.CENTER);
        title.setTextColor(Color.rgb(38,53,43)); errorPanel.addView(title);
        TextView description = new TextView(this);
        description.setText("http".equals(server.getScheme())
            ? "Keep your computer server running and connect USB. Then tap Retry.\n\nسرور کامپیوتر را روشن و گوشی را با USB متصل کنید؛ سپس دوباره تلاش کنید."
            : "Unable to connect. Check your internet connection.\n\nاتصال برقرار نشد. اینترنت را بررسی کنید.");
        description.setTextSize(16); description.setGravity(Gravity.CENTER);
        description.setPadding(0,dp(24),0,dp(24)); errorPanel.addView(description);
        Button retry = new Button(this); retry.setText("Retry / تلاش دوباره");
        retry.setOnClickListener(v -> {errorPanel.setVisibility(View.GONE);web.loadUrl(BuildConfig.SERVER_URL+"/dashboard");});
        errorPanel.addView(retry);errorPanel.setVisibility(View.GONE);
        root.addView(errorPanel,new FrameLayout.LayoutParams(-1,-1));
        setContentView(root);
        root.requestApplyInsets();
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true); // Only user-selected Storage Access Framework CSV URIs.
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSupportMultipleWindows(false);
        settings.setUserAgentString(settings.getUserAgentString()+" GreenMineAndroid/"+BuildConfig.VERSION_NAME);
        if(BuildConfig.BUNDLED_UI){
            settings.setCacheMode(WebSettings.LOAD_DEFAULT);
            String previous=getPreferences(MODE_PRIVATE).getString("ui_version","");
            if(!BuildConfig.VERSION_NAME.equals(previous)){
                web.clearCache(true);
                getPreferences(MODE_PRIVATE).edit().putString("ui_version",BuildConfig.VERSION_NAME).apply();
            }
        }
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);
        web.setBackgroundColor(Color.rgb(226,233,242));
        web.setWebViewClient(mainClient=new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest request){return bundledResource(request);}
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri=request.getUrl();
                if (trusted(uri) && uri.getPath()!=null && uri.getPath().startsWith("/downloads/")) {
                    try {startActivity(new Intent(Intent.ACTION_VIEW,uri));} catch(ActivityNotFoundException ignored) {}
                    return true;
                }
                if (trusted(uri)) return false;
                if (request.isForMainFrame() && ("https".equals(uri.getScheme()) || "mailto".equals(uri.getScheme()))) {
                    try {startActivity(new Intent(Intent.ACTION_VIEW,uri));} catch(ActivityNotFoundException ignored) {}
                }
                return true;
            }
            @Override public void onReceivedError(WebView view,WebResourceRequest req,WebResourceError error) {
                if(req.isForMainFrame()) showConnectionError();
            }
            @Override public void onReceivedHttpError(WebView view,WebResourceRequest req,WebResourceResponse response) {
                if(req.isForMainFrame() && response.getStatusCode()>=400) showConnectionError();
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public void onProgressChanged(WebView view,int value) {
                progress.setProgress(value);progress.setVisibility(value==100?View.GONE:View.VISIBLE);
            }
            @Override public boolean onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params) {
                if(!trusted(Uri.parse(view.getUrl()==null?"":view.getUrl()))) return false;
                if(pendingFile!=null) pendingFile.onReceiveValue(null);
                pendingFile=callback;
                Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*");
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE,params.getMode()==WebChromeClient.FileChooserParams.MODE_OPEN_MULTIPLE);
                intent.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"text/csv","text/comma-separated-values","text/plain","application/csv","application/octet-stream","application/vnd.ms-excel"});
                try {startActivityForResult(intent,PICK_CSV);} catch(ActivityNotFoundException e) {pendingFile.onReceiveValue(null);pendingFile=null;}
                return true;
            }
            // An origin-checked prompt avoids exposing a general JavaScript interface to frames.
            @Override public boolean onJsPrompt(WebView view,String url,String message,String defaultValue,JsPromptResult result) {
                if("greenmine:print".equals(message)) {
                    if(!trusted(Uri.parse(url))) {result.cancel();return true;}
                    try {String html=new JSONObject(defaultValue).getString("html");if(html.length()>2_000_000||reportWeb!=null)throw new IllegalArgumentException();openPdfReport(html);result.confirm("opened");}
                    catch(Exception e){result.cancel();Toast.makeText(MainActivity.this,"PDF unavailable / خطا در خروجی PDF",Toast.LENGTH_LONG).show();}
                    return true;
                }
                if(!"greenmine:export".equals(message)) return false;
                if(!trusted(Uri.parse(url))) {result.cancel();return true;}
                try {
                    JSONObject payload=new JSONObject(defaultValue);
                    String filename=payload.getString("filename"), csv=payload.getString("csv");
                    if(!filename.matches("greenmine-(production|forecast)\\.csv") || csv.length()>2_000_000 || pendingCsv!=null) throw new IllegalArgumentException();
                    pendingCsv=csv;
                    Intent save=new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("text/csv").putExtra(Intent.EXTRA_TITLE,filename);
                    startActivityForResult(save,SAVE_CSV);result.confirm("opened");
                } catch(Exception e) {pendingCsv=null;result.cancel();Toast.makeText(MainActivity.this,"Export unavailable / خطا در خروجی",Toast.LENGTH_LONG).show();}
                return true;
            }
        });
        if(Build.VERSION.SDK_INT>=33) getOnBackInvokedDispatcher().registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT,this::handleBack);
        if(state==null || web.restoreState(state)==null) web.loadUrl(BuildConfig.SERVER_URL+(BuildConfig.BUNDLED_UI?"/":"/dashboard"));
    }
    private void openPdfReport(String html){
        reportWeb=new WebView(this);
        reportWeb.getSettings().setAllowFileAccess(false);
        reportWeb.getSettings().setJavaScriptEnabled(false);
        reportWeb.setWebViewClient(new WebViewClient(){
            private boolean printed=false;
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest request){return bundledResource(request);}
            @Override public void onPageFinished(WebView view,String url){
                if(printed)return;printed=true;
                android.print.PrintManager manager=(android.print.PrintManager)getSystemService(PRINT_SERVICE);
                android.print.PrintDocumentAdapter delegate=view.createPrintDocumentAdapter("GreenMine report");
                manager.print("GreenMine report",new android.print.PrintDocumentAdapter(){
                    @Override public void onStart(){delegate.onStart();}
                    @Override public void onLayout(android.print.PrintAttributes oldAttrs,android.print.PrintAttributes newAttrs,android.os.CancellationSignal signal,LayoutResultCallback callback,Bundle extras){delegate.onLayout(oldAttrs,newAttrs,signal,callback,extras);}
                    @Override public void onWrite(android.print.PageRange[] pages,android.os.ParcelFileDescriptor destination,android.os.CancellationSignal signal,WriteResultCallback callback){delegate.onWrite(pages,destination,signal,callback);}
                    @Override public void onFinish(){delegate.onFinish();view.destroy();if(reportWeb==view)reportWeb=null;}
                },new android.print.PrintAttributes.Builder().setMediaSize(android.print.PrintAttributes.MediaSize.ISO_A4).build());
            }
        });
        reportWeb.loadDataWithBaseURL(BuildConfig.SERVER_URL+"/",html,"text/html","UTF-8",null);
    }
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private WebResourceResponse bundledResource(WebResourceRequest request){
        if(!BuildConfig.BUNDLED_UI||!trusted(request.getUrl())||!"GET".equals(request.getMethod()))return null;
        Uri uri=request.getUrl();String path=uri.getPath();
        if(path==null||path.startsWith("/api/"))return null;
        if(path.contains("..")||path.indexOf('\0')>=0)return missingResource();
        String asset;
        if("/".equals(path)||"/dashboard".equals(path)||"/dashboard/".equals(path)||"/download".equals(path)||"/download/".equals(path)){
            asset="_pages/"+(path.startsWith("/dashboard")?"dashboard":path.startsWith("/download")?"download":"index")+(uri.getQueryParameter("_rsc")!=null?".rsc":".html");
        }else asset=path.startsWith("/")?path.substring(1):path;
        try{
            InputStream body=getAssets().open("web/"+asset);
            String mime=asset.endsWith(".html")?"text/html":asset.endsWith(".rsc")?"text/x-component":asset.endsWith(".js")?"application/javascript":asset.endsWith(".css")?"text/css":asset.endsWith(".woff")?"font/woff":asset.endsWith(".woff2")?"font/woff2":asset.endsWith(".svg")?"image/svg+xml":asset.endsWith(".png")?"image/png":asset.endsWith(".json")?"application/json":"application/octet-stream";
            HashMap<String,String> headers=new HashMap<>();headers.put("Cache-Control","no-store");headers.put("X-GreenMine-UI",BuildConfig.VERSION_NAME);
            return new WebResourceResponse(mime,mime.startsWith("text/")||mime.contains("javascript")?"UTF-8":null,200,"OK",headers,body);
        }catch(IOException ignored){
            if(path.startsWith("/_next/")||path.startsWith("/images/")||path.startsWith("/fonts/"))return missingResource();
            return null;
        }
    }
    private WebResourceResponse missingResource(){return new WebResourceResponse("text/plain","UTF-8",404,"Not Found",new HashMap<>(),new ByteArrayInputStream(new byte[0]));}
    private boolean trusted(Uri uri) {
        return server.getScheme()!=null && server.getScheme().equals(uri.getScheme()) && server.getHost()!=null && server.getHost().equals(uri.getHost()) && server.getPort()==uri.getPort();
    }
    private void showConnectionError(){progress.setVisibility(View.GONE);errorPanel.setVisibility(View.VISIBLE);}
    private void handleBack(){web.evaluateJavascript("(()=>{const close=document.querySelector('[role=dialog] .dialog-close');if(close){close.click();return true}const menu=document.querySelector('.menu-button[aria-expanded=true]');if(menu){menu.click();return true}return false})()",result->{if(!"true".equals(result)){if(web.canGoBack())web.goBack();else finish();}});}
    @Override public void onBackPressed(){handleBack();}
    @Override protected void onSaveInstanceState(Bundle state){super.onSaveInstanceState(state);web.saveState(state);}
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data);
        if(request==PICK_CSV && pendingFile!=null){pendingFile.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(result,data));pendingFile=null;}
        if(request==SAVE_CSV){
            if(result==RESULT_OK && data!=null && data.getData()!=null && pendingCsv!=null){
                try(OutputStream out=getContentResolver().openOutputStream(data.getData())){
                    if(out==null) throw new java.io.IOException();out.write(pendingCsv.getBytes(StandardCharsets.UTF_8));
                    Toast.makeText(this,"CSV saved / فایل ذخیره شد",Toast.LENGTH_SHORT).show();
                }catch(Exception e){Toast.makeText(this,"Could not save / ذخیره انجام نشد",Toast.LENGTH_LONG).show();}
            }
            pendingCsv=null;
        }
    }
    WebView testWebView(){return web;}
    WebResourceResponse testBundledResource(WebResourceRequest request){return bundledResource(request);}
    void testRestoreClient(){web.setWebViewClient(mainClient);}
    @Override protected void onPause(){CookieManager.getInstance().flush();super.onPause();}
    @Override protected void onDestroy(){if(pendingFile!=null)pendingFile.onReceiveValue(null);if(reportWeb!=null){reportWeb.destroy();reportWeb=null;}web.destroy();super.onDestroy();}
}
