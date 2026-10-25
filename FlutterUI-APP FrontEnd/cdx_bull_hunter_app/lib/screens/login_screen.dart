import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'otp_verification_screen.dart'; // अगला स्टेप (OTP स्क्रीन)

class LoginScreen extends StatefulWidget {
  const LoginScreen({Key? key}) : super(key: key);

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final TextEditingController _emailController = TextEditingController();
  bool _isLoading = false;

  // आपका लाइव रेंडर बैकएंड URL
  final String baseUrl = "https://bull-hunter-bot-gbhv9-5.onrender.com";

  // OTP भेजने का फंक्शन
  Future<void> _sendOtp() async {
    final email = _emailController.text.trim();
    if (email.isEmpty || !email.contains('@')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('कृपया एक वैध ईमेल एड्रेस दर्ज करें'), backgroundColor: Colors.red),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/send-otp'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email}),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(data['message'] ?? 'OTP भेजा गया!'), backgroundColor: Colors.green),
        );

        // OTP स्क्रीन पर रीडायरेक्ट करें
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
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: ${e.toString()}'), backgroundColor: Colors.red),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // 1. बैकग्राउंड थीम इमेज या ग्रेडिएंट लेयर (আপনার YouTube चैनल और बोट थीम के अनुसार)
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0xFF0A0F1D), // डार्क थीम बेस
                  Color(0xFF1E293B),
                  Color(0xFF0F172A),
                ],
              ),
            ),
            child: Center(
              child: Opacity(
                opacity: 0.15, // इमेज को बैकग्राउंड में वाटरमार्क जैसा दिखाने के लिए
                child: Image.asset(
                  'assets/images/bot_bg_theme.png', // यहाँ आपके बोट/YouTube लोगो वाली इमेज आएगी
                  fit: BoxFit.cover,
                  width: double.infinity,
                  height: double.infinity,
                  errorBuilder: (context, error, stackTrace) => const Icon(Icons.analytics, size: 200, color: Colors.cyan),
                ),
              ),
            ),
          ),

          // 2. फ्रंट UI कंटेंट्स
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  const SizedBox(height: 40),
                  // बोट और YouTube चैनल की ब्रांडिंग हेडर्स
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

                  // ईमेल इनपुट कार्ड
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
                            onPressed: _isLoading ? null : _sendOtp,
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
                                    'GET OTP / CONTINUE',
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