import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'screens/login_screen.dart';
import 'screens/pin_login_screen.dart'; // सीधे पिन स्क्रीन पर जाने के लिए

void main() async {
  // Flutter bindings ensure karne ke liye
  WidgetsFlutterBinding.ensureInitialized();

  // Local storage se check karein ki kya user pehle se logged-in hai (saved email)
  SharedPreferences prefs = await SharedPreferences.getInstance();
  String? savedEmail = prefs.getString('logged_in_email');

  runApp(BullHunterApp(savedEmail: savedEmail));
}

class BullHunterApp extends StatelessWidget {
  final String? savedEmail;
  const BullHunterApp({Key? key, this.savedEmail}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Bull Hunter Bot',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.cyan,
        scaffoldBackgroundColor: const Color(0xFF0A0F1D),
        brightness: Brightness.dark,
      ),
      // Smart Routing: Agar email saved hai toh PinLoginScreen, warna LoginScreen
      home: savedEmail != null && savedEmail!.isNotEmpty
          ? PinLoginScreen(email: savedEmail!)
          : const LoginScreen(),
    );
  }
}