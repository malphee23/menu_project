// lib/features/auth/guest_or_login_screen.dart
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class GuestOrLoginScreen extends StatelessWidget {
  static const String routeName = '/welcome';

  const GuestOrLoginScreen({super.key});

  Future<void> _setGuestMode(BuildContext context) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('is_guest', true);
    await prefs.setBool('is_logged_in', false);
    Navigator.pushReplacementNamed(context, '/date');
  }

  Future<void> _goToLogin(BuildContext context) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('is_guest', false);
    Navigator.pushReplacementNamed(context, '/login');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text(
                'Добро пожаловать!',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              const Text(
                'Выберите способ входа',
                style: TextStyle(fontSize: 18, color: Colors.grey),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 40),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.blue),
                  onPressed: () => _goToLogin(context),
                  child: const Text('Войти в аккаунт', style: TextStyle(color: Colors.white)),
                ),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: OutlinedButton(
                  onPressed: () => _setGuestMode(context),
                  child: const Text('Войти как гость'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}