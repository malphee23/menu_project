import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class RegisterScreen extends StatefulWidget {
  static const String routeName = '/register';

  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _nameController = TextEditingController();

  Future<void> _register() async {
    if (_formKey.currentState!.validate()) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('is_logged_in', true);
      await prefs.setString('email', _emailController.text);
      await prefs.setString('name', _nameController.text);
      Navigator.pushReplacementNamed(context, '/date');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Регистрация')),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Form(
          key: _formKey,
          child: Column(
            children: [
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'Имя',
                  hintText: 'Введите ваше имя',
                  prefixIcon: Icon(Icons.person),
                ),
                validator: (v) => v!.isEmpty ? 'Введите имя' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _emailController,
                decoration: const InputDecoration(
                  labelText: 'Email',
                  hintText: 'example@mail.com',
                  prefixIcon: Icon(Icons.email),
                ),
                keyboardType: TextInputType.emailAddress,
                validator: (v) {
                  if (v!.isEmpty) return 'Введите email';
                  if (!RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(v)) return 'Неверный формат email';
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _passwordController,
                decoration: const InputDecoration(
                  labelText: 'Пароль',
                  hintText: 'Минимум 6 символов',
                  prefixIcon: Icon(Icons.lock),
                  suffixIcon: Icon(Icons.visibility_off),
                ),
                obscureText: true,
                validator: (v) {
                  if (v!.isEmpty) return 'Введите пароль';
                  if (v.length < 6) return 'Пароль должен быть не менее 6 символов';
                  return null;
                },
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _register,
                  child: const Text('Зарегистрироваться'),
                ),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Уже есть аккаунт? Войти'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}