import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/student_model.dart';
import '../services/api_service.dart';

class AuthProvider extends ChangeNotifier {
  StudentProfile? _student;
  bool _isLoading = false;
  String? _error;

  StudentProfile? get student => _student;
  bool get isLoading => _isLoading;
  bool get isAuthenticated => _student != null;
  String? get error => _error;

  Future<void> loadSavedSession() async {
    final prefs = await SharedPreferences.getInstance();
    final studentJson = prefs.getString('student_profile');
    if (studentJson != null) {
      _student = StudentProfile.fromJson(jsonDecode(studentJson) as Map<String, dynamic>);
      notifyListeners();
    }
  }

  Future<void> demoLogin(String exam, String language, {String name = 'Demo Student'}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final data = await ApiService().demoLogin(exam, language, name: name);
      _student = StudentProfile.fromJson(data);
      await _saveSession();
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> refreshStudent() async {
    if (_student == null) return;
    try {
      final data = await ApiService().getStudent(_student!.studentId);
      _student = StudentProfile.fromJson(data);
      await _saveSession();
      notifyListeners();
    } catch (_) {}
  }

  void updateStudent(StudentProfile updated) {
    _student = updated;
    _saveSession();
    notifyListeners();
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('student_profile');
    _student = null;
    _error = null;
    notifyListeners();
  }

  Future<void> _saveSession() async {
    if (_student == null) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('student_profile', jsonEncode(_student!.toJson()));
  }
}
