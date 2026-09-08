import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'cn.edu.sspu.scpcv.control',
  appName: 'SCP-cv Control',
  webDir: 'dist-app',
  loggingBehavior: 'debug',
  zoomEnabled: false,
  android: {
    allowMixedContent: false,
    captureInput: true,
    minWebViewVersion: 111,
    webContentsDebuggingEnabled: false,
    includePlugins: [
      '@capacitor/app',
      '@capacitor/filesystem',
    ],
  },
  server: {
    hostname: 'localhost',
    androidScheme: 'https',
    cleartext: false,
    allowNavigation: [],
    errorPath: 'unsupported-webview.html',
  },
  plugins: {
    App: {
      disableBackButtonHandler: true,
    },
    CapacitorHttp: {
      enabled: false,
    },
  },
};

export default config;
