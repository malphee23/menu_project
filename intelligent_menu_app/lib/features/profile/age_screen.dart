// lib/features/profile/age_screen.dart
import 'package:flutter/material.dart';
import 'package:intelligent_menu_app/features/profile/profile_service.dart';

class AgeScreen extends StatefulWidget {
  const AgeScreen({super.key});

  @override
  State<AgeScreen> createState() => _AgeScreenState();
}

class _AgeScreenState extends State<AgeScreen> {
  int _age = 18;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Возраст')),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('$_age лет', style: const TextStyle(fontSize: 24)),
            const SizedBox(height: 20),
            Slider(
              value: _age.toDouble(),
              min: 1,
              max: 100,
              divisions: 99,
              label: _age.toString(),
              onChanged: (value) {
                setState(() => _age = value.toInt());
              },
            ),
            const Spacer(),
            ElevatedButton(
              onPressed: () async {
                await ProfileService.saveAge(_age);
                Navigator.pushNamed(context, '/allergies');
              },
              child: const Text('Далее'),
            ),
          ],
        ),
      ),
    );
  }
}