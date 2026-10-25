import 'dart:convert';
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:fl_chart/fl_chart.dart'; // fl_chart package for Equity Charts (Stage 3)

class DashboardScreen extends StatefulWidget {
  final String userEmail;
  const DashboardScreen({Key? key, required this.userEmail}) : super(key: key);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _currentIndex = 0;
  bool _isBotRunning = false;
  bool _isLoadingControl = false;
  Map<String, dynamic> _metrics = {};
  bool _isLoadingMetrics = true;

  // वॉलेट और लाइव पीएनएल के लिए स्टेट्स
  Map<String, dynamic> _walletData = {};
  bool _isLoadingWallet = true;

  // लाइव ओपन पोजीशंस के लिए स्टेट्स
  List<dynamic> _openPositions = [];
  bool _isLoadingPositions = true;
  Timer? _pollingTimer;

  // Sound Toggle State (Stage 5)
  bool _soundAlertsEnabled = true;

  final String baseUrl = "https://bull-hunter-bot-gbhv9-5.onrender.com";

  @override
  void initState() {
    super.initState();
    _fetchAllData();
    
    // हर 4 सेकंड में लाइव डेटा को ऑटो-रिफ्रेश करने के लिए टाइमर
    _pollingTimer = Timer.periodic(const Duration(seconds: 4), (timer) {
      _fetchWalletBalance();
      _fetchOpenPositionsSilently();
    });
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchAllData() async {
    await Future.wait([
      _fetchAnalytics(),
      _checkBotInitialStatus(),
      _fetchWalletBalance(),
      _fetchOpenPositions(),
      _fetchSoundSettings(),
    ]);
  }

  // 🔊 Sound Preference Fetching
  Future<void> _fetchSoundSettings() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/settings/sound-status?email=${widget.userEmail}'),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (mounted) {
          setState(() {
            _soundAlertsEnabled = data['sound_alerts_enabled'] ?? true;
          });
        }
      }
    } catch (e) {
      debugPrint("Error fetching sound settings: $e");
    }
  }

  // 🔊 Sound Preference Updating
  Future<void> _toggleSoundAlerts(bool value) async {
    setState(() => _soundAlertsEnabled = value);
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/settings/sound-toggle'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': widget.userEmail,
          'sound_enabled': value,
        }),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(data['message'] ?? 'Sound preference updated'),
            backgroundColor: Colors.cyanAccent,
            duration: const Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      debugPrint("Error updating sound settings: $e");
    }
  }

  // 🔍 Initial Bot Status Fetching
  Future<void> _checkBotInitialStatus() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/bot/status?email=${widget.userEmail}'),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (mounted) {
          setState(() {
            _isBotRunning = data['is_active'] ?? false;
            _openPositions = data['active_positions'] ?? [];
            _isLoadingPositions = false;
          });
        }
      }
    } catch (e) {
      debugPrint("Error checking initial bot status: $e");
      if (mounted) setState(() => _isLoadingPositions = false);
    }
  }

  // Open Positions Fetching
  Future<void> _fetchOpenPositions() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/bot/status?email=${widget.userEmail}'),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (mounted) {
          setState(() {
            _openPositions = data['active_positions'] ?? [];
            _isLoadingPositions = false;
          });
        }
      }
    } catch (e) {
      if (mounted) setState(() => _isLoadingPositions = false);
    }
  }

  // Background silent fetch for timer
  Future<void> _fetchOpenPositionsSilently() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/bot/status?email=${widget.userEmail}'),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (mounted) {
          setState(() {
            _openPositions = data['active_positions'] ?? [];
            _isBotRunning = data['is_active'] ?? _isBotRunning;
          });
        }
      }
    } catch (e) {
      // Silent catch
    }
  }

  // Live Wallet Balance Fetch
  Future<void> _fetchWalletBalance() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/wallet/balance?email=${widget.userEmail}'),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (mounted) {
          setState(() {
            _walletData = data['wallet'] ?? {};
            _isLoadingWallet = false;
          });
        }
      } else {
        if (mounted) setState(() => _isLoadingWallet = false);
      }
    } catch (e) {
      if (mounted) setState(() => _isLoadingWallet = false);
    }
  }

  // Analytics & Metrics Fetching
  Future<void> _fetchAnalytics() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/analytics/summary?email=${widget.userEmail}'),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (mounted) {
          setState(() {
            _metrics = data['metrics'] ?? {};
            _isLoadingMetrics = false;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoadingMetrics = false);
      }
    }
  }

  // Bot Start / Stop Execution Control
  Future<void> _toggleBot(String action) async {
    setState(() => _isLoadingControl = true);
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/bot/control'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': widget.userEmail,
          'action': action,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        setState(() {
          _isBotRunning = (action == 'start');
        });
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(data['message'] ?? 'Action successful'),
            backgroundColor: Colors.green,
          ),
        );
      } else {
        throw Exception(data['detail'] ?? 'Control failed');
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isLoadingControl = false);
      }
    }
  }

  // Emergency PIN Verification Dialog Popup (Stage 4)
  void _showEmergencyPinDialog() {
    final TextEditingController pinController = TextEditingController();
    bool isSubmittingPin = false;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            return AlertDialog(
              backgroundColor: const Color(0xFF1E293B),
              title: const Row(
                children: [
                  Icon(Icons.lock_outline, color: Colors.redAccent),
                  SizedBox(width: 8),
                  Text(
                    'EMERGENCY CONFIRMATION',
                    style: TextStyle(color: Colors.redAccent, fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Aap emergency kill switch trigger karne ja rahe hain. Isse bot turant ruk jayega. Apni pehchan confirm karne ke liye apna App PIN enter karein:',
                    style: TextStyle(color: Colors.white70, fontSize: 13),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: pinController,
                    keyboardType: TextInputType.number,
                    maxLength: 6,
                    obscureText: true,
                    style: const TextStyle(color: Colors.white, fontSize: 18, letterSpacing: 4),
                    decoration: InputDecoration(
                      hintText: 'Enter App PIN',
                      hintStyle: const TextStyle(color: Colors.white38),
                      filled: true,
                      fillColor: const Color(0xFF0A0F1D),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: BorderSide.none,
                      ),
                      counterText: '',
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: isSubmittingPin ? null : () => Navigator.pop(context),
                  child: const Text('Cancel', style: TextStyle(color: Colors.white54)),
                ),
                ElevatedButton(
                  onPressed: isSubmittingPin
                      ? null
                      : () async {
                          final pin = pinController.text.trim();
                          if (pin.length < 4) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Kripya valid PIN enter karein.'), backgroundColor: Colors.red),
                            );
                            return;
                          }

                          setStateDialog(() => isSubmittingPin = true);

                          try {
                            final response = await http.post(
                              Uri.parse('$baseUrl/api/bot/emergency-stop'),
                              headers: {'Content-Type': 'application/json'},
                              body: jsonEncode({
                                'email': widget.userEmail,
                                'pin': pin,
                              }),
                            );

                            final data = jsonDecode(response.body);

                            if (!mounted) return;
                            Navigator.pop(context);

                            if (response.statusCode == 200) {
                              setState(() {
                                _isBotRunning = false;
                                _openPositions.clear();
                              });
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text(data['message'] ?? 'Emergency stop successful'),
                                  backgroundColor: Colors.redAccent,
                                  duration: const Duration(seconds: 4),
                                ),
                              );
                            } else {
                              throw Exception(data['detail'] ?? 'Emergency stop failed');
                            }
                          } catch (e) {
                            if (!mounted) return;
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text('Error: ${e.toString()}'),
                                backgroundColor: Colors.red,
                              ),
                            );
                          }
                        },
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent, foregroundColor: Colors.white),
                  child: isSubmittingPin
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Text('CONFIRM KILL SWITCH', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1D),
      appBar: AppBar(
        title: const Text(
          'BULL HUNTER DASHBOARD',
          style: TextStyle(
            color: Colors.cyanAccent,
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
        backgroundColor: const Color(0xFF1E293B),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.cyanAccent),
            onPressed: _fetchAllData,
          ),
        ],
      ),
      body: IndexedStack(
        index: _currentIndex,
        children: [
          _buildAnalyticsTab(),
          _buildBotControlTab(),
          _buildTradeLogsTab(),
          _buildApiHealthTab(),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        backgroundColor: const Color(0xFF1E293B),
        selectedItemColor: Colors.cyanAccent,
        unselectedItemColor: Colors.white38,
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.analytics),
            label: 'Analytics',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.smart_toy),
            label: 'Control',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.history),
            label: 'Trades',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.security),
            label: 'Health',
          ),
        ],
      ),
    );
  }

  // TAB 1: ANALYTICS
  Widget _buildAnalyticsTab() {
    if (_isLoadingMetrics && _isLoadingWallet) {
      return const Center(
        child: CircularProgressIndicator(color: Colors.cyanAccent),
      );
    }
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'User: ${widget.userEmail}',
            style: const TextStyle(color: Colors.white70, fontSize: 13),
          ),
          const SizedBox(height: 15),

          // 1. Live Wallet Balance & Current PnL Card
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF1E293B), Color(0xFF0F172A)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.cyanAccent.withOpacity(0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'COINDCX LIVE WALLET',
                      style: TextStyle(color: Colors.cyanAccent, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.1),
                    ),
                    Icon(Icons.account_balance_wallet, color: Colors.cyanAccent, size: 18),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Total Balance', style: TextStyle(color: Colors.white54, fontSize: 11)),
                        const SizedBox(height: 4),
                        Text(
                          '\$${_walletData['total_balance'] ?? '0.00'}',
                          style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        const Text('Current PnL', style: TextStyle(color: Colors.white54, fontSize: 11)),
                        const SizedBox(height: 4),
                        Text(
                          '${_walletData['current_pnl'] ?? '+\$0.00'}',
                          style: TextStyle(
                            color: (_walletData['pnl_is_positive'] ?? true) ? Colors.greenAccent : Colors.redAccent,
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 20),

          // 2. Live Open Positions Card (Stage 2)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.cyanAccent.withOpacity(0.2)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'ACTIVE OPEN POSITIONS',
                      style: TextStyle(color: Colors.cyanAccent, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.1),
                    ),
                    if (_isLoadingPositions)
                      const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.cyanAccent),
                      )
                    else
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: _openPositions.isNotEmpty ? Colors.green.withOpacity(0.2) : Colors.white10,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          '${_openPositions.length} Active',
                          style: TextStyle(
                            color: _openPositions.isNotEmpty ? Colors.greenAccent : Colors.white60,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                _openPositions.isEmpty
                    ? const Padding(
                        padding: EdgeInsets.symmetric(vertical: 12.0),
                        child: Center(
                          child: Text(
                            'No active positions running currently.',
                            style: TextStyle(color: Colors.white54, fontSize: 12),
                          ),
                        ),
                      )
                    : ListView.builder(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: _openPositions.length,
                        itemBuilder: (context, index) {
                          final pos = _openPositions[index];
                          final isBuy = pos['position'] == 'BUY';
                          final pnl = pos['pnl'] ?? 0.0;
                          final pnlColor = pnl >= 0 ? Colors.greenAccent : Colors.redAccent;

                          return Container(
                            margin: const EdgeInsets.only(bottom: 8.0),
                            padding: const EdgeInsets.all(10.0),
                            decoration: BoxDecoration(
                              color: const Color(0xFF0A0F1D),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      pos['symbol'] ?? 'UNKNOWN',
                                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      '${pos['position']} | Size: ${pos['size']}',
                                      style: TextStyle(color: isBuy ? Colors.greenAccent : Colors.orangeAccent, fontSize: 11),
                                    ),
                                  ],
                                ),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.end,
                                  children: [
                                    Text(
                                      'PnL: \$${pnl.toStringAsFixed(2)}',
                                      style: TextStyle(color: pnlColor, fontWeight: FontWeight.bold, fontSize: 13),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      'Entry: ${pos['entry_price']}',
                                      style: const TextStyle(color: Colors.white60, fontSize: 10),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          );
                        },
                      ),
              ],
            ),
          ),

          const SizedBox(height: 20),

          // 3. Portfolio Equity Growth Chart Widget (Stage 3)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.cyanAccent.withOpacity(0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'PORTFOLIO EQUITY GROWTH',
                      style: TextStyle(
                        color: Colors.cyanAccent,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.1,
                      ),
                    ),
                    Icon(Icons.show_chart, color: Colors.cyanAccent, size: 18),
                  ],
                ),
                const SizedBox(height: 20),
                SizedBox(
                  height: 180,
                  child: LineChart(
                    LineChartData(
                      gridData: FlGridData(
                        show: true,
                        drawVerticalLine: false,
                        getDrawingHorizontalLine: (value) => FlLine(
                          color: Colors.white10,
                          strokeWidth: 1,
                        ),
                      ),
                      titlesData: FlTitlesData(
                        rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        bottomTitles: const AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        leftTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 40,
                            getTitlesWidget: (value, meta) {
                              return Text(
                                '\$${value.toInt()}',
                                style: const TextStyle(color: Colors.white54, fontSize: 10),
                              );
                            },
                          ),
                        ),
                      ),
                      borderData: FlBorderData(show: false),
                      lineBarsData: [
                        LineChartBarData(
                          spots: const [
                            FlSpot(0, 200.0),
                            FlSpot(1, 205.5),
                            FlSpot(2, 203.0),
                            FlSpot(3, 212.0),
                            FlSpot(4, 218.5),
                            FlSpot(5, 225.0),
                          ],
                          isCurved: true,
                          color: Colors.cyanAccent,
                          barWidth: 3,
                          isStrokeCapRound: true,
                          dotData: const FlDotData(show: false),
                          belowBarData: BarAreaData(
                            show: true,
                            color: Colors.cyanAccent.withOpacity(0.15),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 20),
          const Text(
            'BOT PERFORMANCE METRICS',
            style: TextStyle(color: Colors.white54, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.1),
          ),
          const SizedBox(height: 10),

          Row(
            children: [
              _metricCard(
                'Net PnL',
                '\$${_metrics['net_pnl'] ?? '0.0'}',
                Colors.greenAccent,
              ),
              const SizedBox(width: 10),
              _metricCard(
                'Win Rate',
                '${_metrics['win_rate_pct'] ?? '0.0'}%',
                Colors.cyanAccent,
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              _metricCard(
                'Total Trades',
                '${_metrics['total_trades'] ?? '0'}',
                Colors.white,
              ),
              const SizedBox(width: 10),
              _metricCard(
                'Max Drawdown',
                '${_metrics['max_drawdown_pct'] ?? '0.0'}%',
                Colors.orangeAccent,
              ),
            ],
          ),
        ],
      ),
    );
  }

  // TAB 2: BOT CONTROL (Stage 4 Emergency Panic Button + Stage 5 Sound Toggle)
  Widget _buildBotControlTab() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              _isBotRunning ? Icons.cloud_done : Icons.cloud_off,
              size: 80,
              color: _isBotRunning ? Colors.greenAccent : Colors.redAccent,
            ),
            const SizedBox(height: 20),
            Text(
              _isBotRunning ? 'BOT IS LIVE & TRADING' : 'BOT IS STOPPED',
              style: TextStyle(
                color: _isBotRunning ? Colors.greenAccent : Colors.redAccent,
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 30),
            SizedBox(
              width: double.infinity,
              height: 55,
              child: ElevatedButton(
                onPressed: _isLoadingControl
                    ? null
                    : () => _toggleBot(_isBotRunning ? 'stop' : 'start'),
                style: ElevatedButton.styleFrom(
                  backgroundColor:
                      _isBotRunning ? Colors.redAccent : Colors.greenAccent,
                  foregroundColor: Colors.black,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: _isLoadingControl
                    ? const CircularProgressIndicator(color: Colors.black)
                    : Text(
                        _isBotRunning
                            ? 'STOP AUTOMATED BOT'
                            : 'START AUTOMATED BOT',
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
              ),
            ),
            const SizedBox(height: 20),
            
            // EMERGENCY PANIC BUTTON (Stage 4)
            SizedBox(
              width: double.infinity,
              height: 55,
              child: ElevatedButton.icon(
                onPressed: _isLoadingControl ? null : _showEmergencyPinDialog,
                icon: const Icon(Icons.warning_amber_rounded, color: Colors.white, size: 24),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red.shade900,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                    side: const BorderSide(color: Colors.redAccent, width: 1.5),
                  ),
                ),
                child: const Text(
                  'EMERGENCY KILL SWITCH',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.1,
                  ),
                ),
              ),
            ),

            const SizedBox(height: 25),

            // SOUND ALERTS TOGGLE SWITCH (Stage 5)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white10),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Icon(
                        _soundAlertsEnabled ? Icons.volume_up : Icons.volume_off,
                        color: _soundAlertsEnabled ? Colors.cyanAccent : Colors.white38,
                      ),
                      const SizedBox(width: 12),
                      const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Audio & Speech Alerts',
                            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                          ),
                          Text(
                            'Enable TTS trade execution audio',
                            style: TextStyle(color: Colors.white54, fontSize: 11),
                          ),
                        ],
                      ),
                    ],
                  ),
                  Switch(
                    value: _soundAlertsEnabled,
                    activeColor: Colors.cyanAccent,
                    onChanged: (val) => _toggleSoundAlerts(val),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // TAB 3: TRADE LOGS
  Widget _buildTradeLogsTab() {
    return const Center(
      child: Text(
        'Recent trades data will appear here...',
        style: TextStyle(color: Colors.white54),
      ),
    );
  }

  // TAB 4: API HEALTH
  Widget _buildApiHealthTab() {
    return const Center(
      child: Text(
        'CoinDCX API & Supabase Connection: Active',
        style: TextStyle(color: Colors.greenAccent),
      ),
    );
  }

  Widget _metricCard(String title, String value, Color valueColor) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(color: Colors.white54, fontSize: 12),
            ),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                color: valueColor,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}