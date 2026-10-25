import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dashboard_screen.dart'; // 4-टैब डैशबोर्ड स्क्रीन

class RegistrationScreen extends StatefulWidget {
  final String email;
  const RegistrationScreen({Key? key, required this.email}) : super(key: key);

  @override
  State<RegistrationScreen> createState() => _RegistrationScreenState();
}

class _RegistrationScreenState extends State<RegistrationScreen> {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _apiKeyController = TextEditingController();
  final TextEditingController _apiSecretController = TextEditingController();
  final TextEditingController _telegramTokenController = TextEditingController();
  final TextEditingController _telegramChatIdController = TextEditingController();
  bool _isLoading = false;

  // आपका लाइव रेंडर बैकएंड URL
  final String baseUrl = "https://bull-hunter-bot-gbhv9-5.onrender.com";

  // यूजर रजिस्ट्रेशन और CoinDCX Pre-flight Validation फंक्शन
  Future<void> _registerUser() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/user/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'full_name': _nameController.text.trim(),
          'email': widget.email,
          'phone_number': _phoneController.text.trim(),
          'coindcx_api_key': _apiKeyController.text.trim(),
          'coindcx_secret': _apiSecretController.text.trim(),
          'telegram_token': _telegramTokenController.text.trim(),
          'telegram_chat_id': _telegramChatIdController.text.trim(),
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(data['message'] ?? 'Registration Successful!'), backgroundColor: Colors.green),
        );

        // सीधे मुख्य 4-टैब डैशबोर्ड पर रीडायरेक्ट करें
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(
            builder: (context) => DashboardScreen(userEmail: widget.email),
          ),
          (route) => false,
        );
      } else {
        throw Exception(data['detail'] ?? 'Registration failed');
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
        title: const Text('New User Registration', style: TextStyle(color: Colors.white, fontSize: 18)),
        backgroundColor: const Color(0xFF1E293B),
        iconTheme: const IconThemeData(color: Colors.cyanAccent),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'बोट सेटअप और API क्रेडेंशियल्स',
                style: TextStyle(color: Colors.cyanAccent, fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 5),
              Text(
                'Email: ${widget.email}',
                style: const TextStyle(color: Colors.white60, fontSize: 14),
              ),
              const SizedBox(height: 20),
              
              // Full Name
              TextFormField(
                controller: _nameController,
                style: const TextStyle(color: Colors.white),
                decoration: _inputDecoration('Full Name', Icons.person),
                validator: (value) => value!.isEmpty ? 'कृपया अपना पूरा नाम दर्ज करें' : null,
              ),
              const SizedBox(height: 15),

              // Phone Number
              TextFormField(
                controller: _phoneController,
                keyboardType: TextInputType.phone,
                style: const TextStyle(color: Colors.white),
                decoration: _inputDecoration('Phone Number', Icons.phone),
                validator: (value) => value!.isEmpty ? 'कृपया फोन नंबर दर्ज करें' : null,
              ),
              const SizedBox(height: 15),

              // CoinDCX API Key
              TextFormField(
                controller: _apiKeyController,
                style: const TextStyle(color: Colors.white),
                decoration: _inputDecoration('CoinDCX API Key', Icons.key),
                validator: (value) => value!.isEmpty ? 'API Key आवश्यक है' : null,
              ),
              const SizedBox(height: 15),

              // CoinDCX Secret Key
              TextFormField(
                controller: _apiSecretController,
                obscureText: true,
                style: const TextStyle(color: Colors.white),
                decoration: _inputDecoration('CoinDCX Secret Key', Icons.lock),
                validator: (value) => value!.isEmpty ? 'Secret Key आवश्यक है' : null,
              ),
              const SizedBox(height: 15),

              // Telegram Token (Optional)
              TextFormField(
                controller: _telegramTokenController,
                style: const TextStyle(color: Colors.white),
                decoration: _inputDecoration('Telegram Bot Token (Optional)', Icons.telegram),
              ),
              const SizedBox(height: 15),

              // Telegram Chat ID (Optional)
              TextFormField(
                controller: _telegramChatIdController,
                style: const TextStyle(color: Colors.white),
                decoration: _inputDecoration('Telegram Chat ID (Optional)', Icons.chat),
              ),
              const SizedBox(height: 30),

              // Submit Button
              SizedBox(
                width: double.infinity,
                height: 55,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _registerUser,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.cyanAccent,
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  child: _isLoading
                      ? const CircularProgressIndicator(color: Colors.black)
                      : const Text(
                          'VERIFY & REGISTER',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  InputDecoration _inputDecoration(String label, IconData icon) {
    return InputDecoration(
      labelText: label,
      labelStyle: const TextStyle(color: Colors.white54),
      prefixIcon: Icon(icon, color: Colors.cyanAccent),
      filled: true,
      fillColor: const Color(0xFF1E293B),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide.none,
      ),
    );
  }
}