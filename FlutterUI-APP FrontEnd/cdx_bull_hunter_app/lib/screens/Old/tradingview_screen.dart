import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class TradingViewScreen extends StatefulWidget {
  final String userEmail;

  const TradingViewScreen({Key? key, required this.userEmail}) : super(key: key);

  @override
  State<TradingViewScreen> createState() => _TradingViewScreenState();
}

class _TradingViewScreenState extends State<TradingViewScreen> {
  late final WebViewController _controller;
  WebSocketChannel? _channel;
  bool _isLoading = true;

  // TradingView Lightweight Charts ka HTML code
  final String _chartHtml = '''
  <!DOCTYPE html>
  <html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
      body { margin: 0; padding: 0; background-color: #0F172A; overflow: hidden; }
      #chart { width: 100vw; height: 100vh; }
    </style>
  </head>
  <body>
    <div id="chart"></div>
    <script>
      const chart = LightweightCharts.createChart(document.getElementById('chart'), {
        layout: { backgroundColor: '#0F172A', textColor: '#D9D9D9' },
        grid: { vertLines: { color: '#1E293B' }, horzLines: { color: '#1E293B' } },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        priceScale: { borderColor: '#334155' },
        timeScale: { borderColor: '#334155', timeVisible: true, secondsVisible: true },
      });

      const lineSeries = chart.addLineSeries({
        color: '#38BDF8',
        lineWidth: 2,
      });

      // Flutter se Javascript ke dwara new price tick update karne ka function
      function updateTickPrice(price, timestamp) {
        lineSeries.update({
          time: timestamp,
          value: price
        });
      }
    </script>
  </body>
  </html>
  ''';

  @override
  void initState() {
    super.initState();
    _initWebView();
    _connectWebSocket();
  }

  void _initWebView() {
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFF0F172A))
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageFinished: (String url) {
            setState(() {
              _isLoading = false;
            });
          },
        ),
      )
      ..loadHtmlString(_chartHtml);
  }

  void _connectWebSocket() {
    // Render ya local backend ke WebSocket endpoint se connect karein
    final wsUrl = Uri.parse('wss://bull-hunter-bot-gbhv9-5.onrender.com/ws/bot-status/${widget.userEmail}');
    _channel = WebSocketChannel.connect(wsUrl);

    _channel!.stream.listen((message) {
      final data = jsonDecode(message);
      
      // Agar backend se live price tick milta hai
      if (data.containsKey('price')) {
        double price = (data['price'] as num).toDouble();
        int timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;

        // WebView mein JavaScript function execute karke chart update karna
        _controller.runJavaScript('updateTickPrice($price, $timestamp);');
      }
    }, onError: (error) {
      print("WebSocket Error in Chart: $error");
    });
  }

  @override
  void dispose() {
    _channel?.sink.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Live Real-Time Price Chart'),
        backgroundColor: const Color(0xFF0F172A),
      ),
      body: Stack(
        children: [
          WebViewWidget(controller: _controller),
          if (_isLoading)
            const Center(
              child: CircularProgressIndicator(color: Color(0xFF38BDF8)),
            ),
        ],
      ),
    );
  }
}