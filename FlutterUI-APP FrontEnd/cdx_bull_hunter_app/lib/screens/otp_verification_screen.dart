import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart'; // 🔑 Persistent session ke liye zaroori package
import 'registration_screen.dart'; // नया यूजर रजिस्ट्रेशन स्क्रीन
import 'pin_login_screen.dart';   // पुराना यूजर जिनके पास PIN है
import 'set_pin_screen.dart';     // पुराना यूजर जिनके पास PIN नहीं है

class OtpVerificationScreen extends StatefulWidget {
  final String email;
  const OtpVerificationScreen({Key? key, required this.email}) : super(key: key);

  @override
  State<OtpVerificationScreen> createState() => _OtpVerificationScreenState();
}

class _OtpVerificationScreenState extends State<OtpVerificationScreen> {
  final TextEditingController _otpController = TextEditingController();
  bool _isLoading = false;

  // आपका लाइव रेंडर बैकएंड URL
  final String baseUrl = "https://bull-hunter-bot-gbhv9-5.onrender.com";

  // OTP वेरीफाई करने और डेटाबेस स्टेटस चेक करने का फंक्शन
  Future<void> _verifyOtp() async {
    final otp = _otpController.text.trim();
    if (otp.length != 6) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('कृपया 6-डिजिट का वैध OTP दर्ज करें'), backgroundColor: Colors.red),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/verify-otp'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': widget.email,
          'otp': otp,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        // 🔑 STAGE 1: OTP सफल होने पर SharedPreferences में ईमेल लोकली सेव करें
        SharedPreferences prefs = await SharedPreferences.getInstance();
        await prefs.setString('logged_in_email', widget.email.trim().toLowerCase());

        bool isRegistered = data['is_registered'] ?? false;
        bool hasPin = data['has_pin'] ?? false;

        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(data['message'] ?? 'OTP Verified!'), backgroundColor: Colors.green),
        );

        // डेटाबेस स्टेटस के आधार पर स्मार्ट नेविगेशन
        if (isRegistered && hasPin) {
          // पुराना यूजर + पिन सेट है -> PIN Login Screen पर जाएं
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(builder: (context) => PinLoginScreen(email: widget.email)),
          );
        } else if (isRegistered && !hasPin) {
          // पुराना यूजर + पिन सेट नहीं है -> Set PIN Screen पर जाएं
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(builder: (context) => SetPinScreen(email: widget.email)),
          );
        } else {
          // नया यूजर -> Registration Screen पर जाएं
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(
              builder: (context) => RegistrationScreen(email: widget.email),
            ),
          );
        }
      } else {
        throw Exception(data['detail'] ?? 'OTP verification failed');
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
      backgroundColor: const Color(0xFF0A0F1D),
      appBar: AppBar(
        title: const Text('Verify OTP', style: TextStyle(color: Colors.white, fontSize: 18)),
        backgroundColor: const Color(0xFF1E293B),
        iconTheme: const IconThemeData(color: Colors.cyanAccent),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 20),
            Text(
              'कोड दर्ज करें: ${widget.email}',
              style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            const Text(
              'आपके ईमेल पर भेजा गया 6-डिजिट का वेरिफिकेशन कोड यहाँ दर्ज करें।',
              style: TextStyle(color: Colors.white70, fontSize: 13),
            ),
            const SizedBox(height: 30),
            TextField(
              controller: _otpController,
              keyboardType: TextInputType.number,
              maxLength: 6,
              style: const TextStyle(color: Colors.white, fontSize: 22, letterSpacing: 8),
              decoration: InputDecoration(
                labelText: '6-Digit OTP',
                labelStyle: const TextStyle(color: Colors.white54),
                prefixIcon: const Icon(Icons.lock_clock, color: Colors.cyanAccent),
                filled: true,
                fillColor: const Color(0xFF1E293B),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
                counterText: '',
              ),
            ),
            const SizedBox(height: 30),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _verifyOtp,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.cyanAccent,
                  foregroundColor: Colors.black,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: _isLoading
                    ? const CircularProgressIndicator(color: Colors.black)
                    : const Text(
                        'VERIFY & CHECK STATUS',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}