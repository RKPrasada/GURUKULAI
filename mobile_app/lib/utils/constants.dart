import 'package:flutter/material.dart';

class AppConstants {
  static const appName = 'VidyaBot';
  static const appTagline = 'AI Tutor for Indian Competitive Exams';

  static const supportedExams = ['RRB NTPC', 'NDA', 'JEE', 'NEET'];
  static const examKeys = ['rrb_ntpc', 'nda', 'jee', 'neet'];
  static const examDescriptions = [
    'Railway Recruitment Board',
    'National Defence Academy',
    'Joint Entrance Examination',
    'National Eligibility cum Entrance Test',
  ];

  static const languages = ['English', 'हिंदी'];
  static const languageKeys = ['en', 'hi'];

  static const difficultyLabels = {1: 'Easy', 2: 'Medium', 3: 'Hard'};
  static const difficultyLabelsHi = {1: 'आसान', 2: 'मध्यम', 3: 'कठिन'};
  static const difficultyColors = {
    1: Color(0xFF43A047),
    2: Color(0xFFFF9800),
    3: Color(0xFFE53935),
  };

  static const weekColors = [
    Color(0xFFE8EAF6),
    Color(0xFFE3F2FD),
    Color(0xFFF3E5F5),
    Color(0xFFE8F5E9),
    Color(0xFFFFF8E1),
    Color(0xFFFBE9E7),
    Color(0xFFE0F7FA),
  ];
}
