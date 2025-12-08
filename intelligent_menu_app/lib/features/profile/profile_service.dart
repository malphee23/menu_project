import 'package:shared_preferences/shared_preferences.dart';

class ProfileService {
  static Future<void> saveBirthDate(DateTime date) async {
    final formatted = '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('birth_date', formatted);
  }

  static Future<void> saveCategory(String category) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('category', category);
  }

  static Future<void> saveAllergies(List<String> allergies) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('allergies', allergies.join(', '));
  }

  static Future<void> saveRestrictions(List<String> restrictions) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('restrictions', restrictions.join(', '));
  }
}