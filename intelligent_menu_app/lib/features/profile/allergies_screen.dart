// lib/features/profile/allergies_screen.dart
import 'package:flutter/material.dart';
import 'package:intelligent_menu_app/features/profile/profile_service.dart';

class AllergiesScreen extends StatefulWidget {
  const AllergiesScreen({super.key});

  @override
  State<AllergiesScreen> createState() => _AllergiesScreenState();
}

class _AllergiesScreenState extends State<AllergiesScreen> {
  final List<Map<String, String>> options = [
    {'label': 'Бобы', 'image': 'beans.png'},
    {'label': 'Орехи', 'image': 'nuts.png'},
    {'label': 'Воздух', 'image': 'air.png'},
    {'label': 'Американо', 'image': 'americano.png'},
    {'label': 'Вода', 'image': 'water.png'},
    {'label': 'Нет аллергии', 'image': 'no_allergy.png'},
  ];

  final Set<String> _selected = {'Нет аллергии'};

  void _toggleSelection(String label) {
    setState(() {
      if (_selected.contains(label)) {
        _selected.remove(label);
      } else {
        _selected.add(label);
        if (label != 'Нет аллергии' && _selected.contains('Нет аллергии')) {
          _selected.remove('Нет аллергии');
        }
        if (_selected.isEmpty) {
          _selected.add('Нет аллергии');
        }
      }
    });
  }

  void _exitSession(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Завершить сеанс?'),
        content: const Text('Все несохранённые данные будут потеряны.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Отмена')),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              Navigator.of(context).pushNamedAndRemoveUntil('/login', (route) => false);
            },
            child: const Text('Выйти'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Аллергены'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.close, color: Colors.grey, size: 30),
            onPressed: () => _exitSession(context),
          ),
        ],
      ),
      body: GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
        ),
        itemCount: options.length,
        itemBuilder: (context, index) {
          final item = options[index];
          final isSelected = _selected.contains(item['label']);
          return GestureDetector(
            onTap: () => _toggleSelection(item['label']!),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    color: isSelected ? Colors.blue.withOpacity(0.2) : Colors.grey[200],
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: isSelected ? Colors.blue : Colors.transparent,
                      width: 2,
                    ),
                  ),
                  child: ClipOval(
                    child: Image.asset('assets/images/${item['image']}', fit: BoxFit.cover),
                  ),
                ),
                const SizedBox(height: 8),
                Text(item['label']!, textAlign: TextAlign.center, style: const TextStyle(fontSize: 14)),
              ],
            ),
          );
        },
      ),
      floatingActionButton: ElevatedButton(
        onPressed: () async {
          await ProfileService.saveAllergies(_selected.toList());
          Navigator.pushNamed(context, '/restrictions');
        },
        child: const Text('Далее'),
      ),
    );
  }
}