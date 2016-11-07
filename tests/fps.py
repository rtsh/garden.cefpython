from kivy.app import App
from kivy.garden.cefpython import CEFBrowser

CEFBrowser.update_flags({'enable-fps': True})

if __name__ == '__main__':
    class SimpleBrowserApp(App):
        def build(self):
            return CEFBrowser(url="https://www.vsynctester.com")

    SimpleBrowserApp().run()
