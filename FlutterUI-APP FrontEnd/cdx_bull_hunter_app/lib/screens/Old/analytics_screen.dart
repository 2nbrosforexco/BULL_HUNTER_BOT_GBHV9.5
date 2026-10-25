import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class AnalyticsScreen extends StatefulWidget {
  final String userEmail;

  const AnalyticsScreen({Key? key, required this.userEmail}) : super(key: key);

  @override
  _AnalyticsScreenState createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  bool _isLoading = true;
  Map<String, dynamic> _metrics = {};

  @override
  void initState() {
    super.initState();
    _fetchAnalytics();
  }

  Future<void> _fetchAnalytics() async {
    setState(() => _isLoading = true);

    String url = 'https://bull-hunter-bot-gbhv9-5.onrender.com/api/analytics/summary?email=${widget.userEmail}';

    try {
      final response = await http.get(Uri.parse(url));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['status'] == 'success') {
          setState(() {
            _metrics = data['metrics'] ?? {};
          });
        }
      }
    } catch (e) {
      print("Error fetching analytics: $e");
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Analytics Summary'),
        backgroundColor: const Color(0xFF0F172A),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _fetchAnalytics),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(16.0),
              child: GridView.count(
                crossAxisCount: 2,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                children: [
                  _buildMetricCard('Total Trades', '${_metrics['total_trades'] ?? 0}', Icons.show_chart, Colors.blue),
                  _buildMetricCard('Net PnL', '₹${_metrics['net_pnl'] ?? 0.0}', Icons.trending_up, (_metrics['net_pnl'] ?? 0) >= 0 ? Colors.green : Colors.red),
                  _buildMetricCard('Win Rate', '${_metrics['win_rate_pct'] ?? 0.0}%', Icons.pie_chart, Colors.orange),
                  _buildMetricCard('Max Drawdown', '${_metrics['max_drawdown_pct'] ?? 0.0}%', Icons.warning_amber, Colors.redAccent),
                ],
              ),
            ),
    );
  }

  Widget _buildMetricCard(String title, String value, IconData icon, Color color) {
    return Card(
      elevation: 4,
      color: const Color(0xFF1E293B),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 34, color: color),
            const SizedBox(height: 8),
            Text(title, style: const TextStyle(fontSize: 13, color: Colors.grey)),
            const SizedBox(height: 4),
            Text(value, style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: color)),
          ],
        ),
      ),
    );
  }
}