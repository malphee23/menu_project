// lib/features/profile/date_screen.dart
import 'package:flutter/material.dart';
import 'package:intelligent_menu_app/features/profile/profile_service.dart';

class DateScreen extends StatefulWidget {
  const DateScreen({super.key});

  @override
  State<DateScreen> createState() => _DateScreenState();
}

class _DateScreenState extends State<DateScreen> {
  late DateTime _selectedDate;

  @override
  void initState() {
    _selectedDate = DateTime.now();
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Дата рождения')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            CalendarDatePicker(
              firstDate: DateTime(1900),
              lastDate: DateTime.now(),
              currentDate: _selectedDate,
              initialDate: _selectedDate,
              onDateChanged: (date) {
                setState(() => _selectedDate = date);
              },
            ),
            const Spacer(),
            ElevatedButton(
              onPressed: () async {
                await ProfileService.saveAge(_selectedDate.year);
                Navigator.pushReplacementNamed(context, '/category');
              },
              child: const Text('Далее'),
            ),
          ],
        ),
      ),
    );
  }
}