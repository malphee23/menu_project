import 'package:flutter/material.dart';

class CloseButtonWidget extends StatelessWidget {
  final VoidCallback onDismiss;

  const CloseButtonWidget({super.key, required this.onDismiss});

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: 24,
      right: 16,
      child: IconButton(
        icon: const Icon(Icons.close, color: Colors.grey, size: 30),
        onPressed: onDismiss,
      ),
    );
  }
}