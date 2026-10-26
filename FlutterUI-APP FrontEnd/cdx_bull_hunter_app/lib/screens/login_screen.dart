import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'otp_verification_screen.dart';
import 'pin_verification_screen.dart'; // Ensure karein ki ye screen imported ho

class LoginScreen extends StatefulWidget {
  const LoginScreen({Key? key}) : super(key: key);

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final TextEditingController _emailController = TextEditingController();
  bool _isLoading = false;

  final String baseUrl = "https://bull-hunter-bot-gbhv9-5.onrender.com";

  // 🔍 Email check karne aur conditional routing ka main function
  Future<void> _checkUserAndProceed() async {
    final email = _emailController.text.trim().toLowerCase();
    if (email.isEmpty || !email.contains('@')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('कृपया एक वैध ईमेल एड्रेस दर्ज करें'), backgroundColor: Colors.red),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      // Backend se check karein ki user pehle se registered hai ya nahi
      final response = await http.get(
        Uri.parse('$baseUrl/api/auth/check-status?email=$email'),
        headers: {'Content-Type': 'application/json'},
      );

      debugPrint("Check Status Response Code: ${response.statusCode}");
      debugPrint("Check Status Response Body: ${response.body}");

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        bool isRegistered = data['is_registered'] ?? false;
        bool hasPin = data['has_pin'] ?? false;

        if (!mounted) return;

        if (isRegistered && hasPin) {
          // Agar user registered hai aur PIN set hai, toh seedha PIN screen par bhein
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => PinVerificationScreen(email: email),
            ),
          );
        } else {
          // Agar naya user hai, toh OTP generate karke OTP screen par bhein
          await _sendOtp(email);
        }
      } else {
        // Agar backend error de, toh user ko alert dikhayein ya debug karein
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('यूजर स्टेटस जाँचने में विफल (Code: ${response.statusCode})'), backgroundColor: Colors.orange),
        );
      }
    } catch (e) {
      debugPrint("Login Check Error: $e");
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('कनेक्शन त्रुटि: ${e.toString()}'), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  // 📤 OTP bhejne ka helper function
  Future<void> _sendOtp(String email) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/send-otp'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email}),
      );

      final data = jsonDecode(response.body);

      if (!mounted) return;

      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(data['message'] ?? 'OTP भेजा गया!'), backgroundColor: Colors.green),
        );

        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => OtpVerificationScreen(email: email),
          ),
        );
      } else {
        throw Exception(data['detail'] ?? 'OTP भेजने में विफल');
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: ${e.toString()}'), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0xFF0A0F1D),
                  Color(0xFF1E293B),
                  Color(0xFF0F172A),
                ],
              ),
            ),
            child: Center(
              child: Opacity(
                opacity: 0.15,
                child: Image.asset(
                  'assets/images/bot_bg_theme.png',
                  fit: BoxFit.cover,
                  width: double.infinity,
                  height: double.infinity,
                  errorBuilder: (context, error, stackTrace) => const Icon(Icons.analytics, size: 200, color: Colors.cyan),
                ),
              ),
            ),
          ),
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  const SizedBox(height: 40),
                  const CircleAvatar(
                    radius: 45,
                    backgroundColor: Colors.cyanAccent,
                    child: Icon(Icons.show_chart, size: 50, color: Colors.black),
                  ),
                  const SizedBox(height: 20),
                  const Text(
                    'BULL HUNTER BOT',
                    style: TextStyle(
                      color: Colors.cyanAccent,
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1.5,
                    ),
                  ),
                  const SizedBox(height: 5),
                  const Text(
                    'Powered by : 2NBROS_FOREXCO',
                    style: TextStyle(color: Colors.white60, fontSize: 13),
                  ),
                  const SizedBox(height: 60),
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1E293B).withOpacity(0.85),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: Colors.cyanAccent.withOpacity(0.3)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Secure Login / Register',
                          style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 10),
                        const Text(
                          'अपने रजिस्टर्ड या नए ईमेल से शुरुआत करें:',
                          style: TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                        const SizedBox(height: 20),
                        TextField(
                          controller: _emailController,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            labelText: 'Email Address',
                            labelStyle: const TextStyle(color: Colors.white54),
                            prefixIcon: const Icon(Icons.email, color: Colors.cyanAccent),
                            filled: true,
                            fillColor: const Color(0xFF0F172A),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide.none,
                            ),
                          ),
                        ),
                        const SizedBox(height: 25),
                        SizedBox(
                          width: double.infinity,
                          height: 50,
                          child: ElevatedButton(
                            onPressed: _isLoading ? null : _checkUserAndProceed,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.cyanAccent,
                              foregroundColor: Colors.black,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            child: _isLoading
                                ? const CircularProgressIndicator(color: Colors.black)
                                : const Text(
                                    'CONTINUE',
                                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                                  ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}