import threading
import time
import sys
import os

# Start LocalConvert Flask backend in background thread
def start_backend():
    try:
        from app import app
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    except Exception as err:
        print(f"Backend error: {err}")

# Launch backend thread
backend_thread = threading.Thread(target=start_backend)
backend_thread.daemon = True
backend_thread.start()

# Android Kivy App Wrapper
try:
    from kivy.app import App
    from kivy.uix.widget import Widget
    from jnius import autoclass
    from android.runnable import run_on_ui_thread

    WebView = autoclass('android.webkit.WebView')
    WebViewClient = autoclass('android.webkit.WebViewClient')
    activity = autoclass('org.kivy.android.PythonActivity').mActivity

    class LocalConvertApp(App):
        def build(self):
            self.create_webview()
            return Widget()

        @run_on_ui_thread
        def create_webview(self):
            webview = WebView(activity)
            webview.getSettings().setJavaScriptEnabled(True)
            webview.getSettings().setDomStorageEnabled(True)
            webview.getSettings().setAllowFileAccess(True)
            webview.getSettings().setAllowContentAccess(True)
            webview.setWebViewClient(WebViewClient())
            activity.setContentView(webview)
            webview.loadUrl('http://127.0.0.1:5000')

    if __name__ == '__main__':
        LocalConvertApp().run()

except ImportError:
    # Desktop / CLI Fallback
    import webbrowser
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')
    from app import app
    app.run(host='127.0.0.1', port=5000)
