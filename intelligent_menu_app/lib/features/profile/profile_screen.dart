import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ProfileScreen extends StatefulWidget {
  final String category;

  const ProfileScreen({super.key, required this.category});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  // Контроллеры
  final _ageController = TextEditingController();

  // Выбранные значения
  String? _selectedAllergy;
  String? _selectedDiet;
  String? _selectedStyle;

  // Варианты
  static const List<String> allergies = [
    'Нет',
    'Орехи',
    'Лактоза',
    'Глютен',
    'Яйца',
    'Морепродукты',
    'Соевые продукты'
  ];

  static const List<String> diets = [
    'Нет',
    'Правильное питание (ПП)',
    'Вегетарианство',
    'Веганство',
    'Сыроедение',
    'Кето',
    'Палео',
    'Без сахара',
    'Низкоуглеводная диета'
  ];

  static const List<String> styles = [
    'Быстро',
    'Романтический ужин',
    'Дружеская вечеринка',
    'Деловой обед',
    'Семейный ужин',
    'Соло-приём пищи'
  ];

  Future<void> _saveProfile() async {
    if (_ageController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Укажите возраст')),
      );
      return;
    }

    final age = int.tryParse(_ageController.text);
    if (age == null || age < 1 || age > 120) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Возраст от 1 до 120')),
      );
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('category', widget.category);
    await prefs.setInt('age', age);
    await prefs.setString('allergies', _selectedAllergy ?? 'Нет');
    await prefs.setString('diet', _selectedDiet ?? 'Нет');
    await prefs.setString('style', _selectedStyle ?? 'Быстро');

    Navigator.pop(context);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Профиль сохранён!')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Ваш профиль')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: SingleChildScrollView(
          child: Column(
            children: [
              // Возраст
              TextField(
                controller: _ageController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Возраст',
                  hintText: 'Например: 25',
                ),
              ),
              const SizedBox(height: 16),

              // Диетические ограничения
              DropdownButtonFormField<String>(
                value: _selectedAllergy,
                hint: const Text('Выберите ограничение'),
                decoration: const InputDecoration(
                  labelText: 'Диетические ограничения',
                ),
                items: allergies.map((allergy) {
                  return DropdownMenuItem(value: allergy, child: Text(allergy));
                }).toList(),
                onChanged: (value) {
                  setState(() {
                    _selectedAllergy = value;
                  });
                },
              ),
              const SizedBox(height: 16),

              // Режим питания
              DropdownButtonFormField<String>(
                value: _selectedDiet,
                hint: const Text('Выберите режим'),
                decoration: const InputDecoration(
                  labelText: 'Режим питания',
                ),
                items: diets.map((diet) {
                  return DropdownMenuItem(value: diet, child: Text(diet));
                }).toList(),
                onChanged: (value) {
                  setState(() {
                    _selectedDiet = value;
                  });
                },
              ),
              const SizedBox(height: 16),

              // Стиль приёма пищи
              DropdownButtonFormField<String>(
                value: _selectedStyle,
                hint: const Text('Выберите стиль'),
                decoration: const InputDecoration(
                  labelText: 'Стиль приёма пищи',
                ),
                items: styles.map((style) {
                  return DropdownMenuItem(value: style, child: Text(style));
                }).toList(),
                onChanged: (value) {
                  setState(() {
                    _selectedStyle = value;
                  });
                },
              ),
              const SizedBox(height: 24),

              // Кнопка сохранения
              ElevatedButton(
                onPressed: _saveProfile,
                child: const Text('Продолжить'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}