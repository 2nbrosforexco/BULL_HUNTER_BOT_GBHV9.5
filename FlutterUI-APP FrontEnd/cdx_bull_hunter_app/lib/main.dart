import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:webview_flutter_platform_interface/webview_flutter_platform_interface.dart';
import 'package:webview_flutter_web/webview_flutter_web.dart';

// ✅ Dashboard ki jagah ab RegisterScreen ko import karein
import 'screens/register_screen.dart'; 

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // ✅ Web platform ke liye WebView instance yahan set karein
  if (kIsWeb) {
    WebViewPlatform.instance = WebWebViewPlatform();
  }

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CDX Bull Hunter Bot',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0A0F1D),
        primarySwatch: Colors.cyan,
      ),
      // ✅ App khulte hi RegisterScreen load hogi jo purane session ko check karegi
      home: const RegisterScreen(), 
    );
  }
}