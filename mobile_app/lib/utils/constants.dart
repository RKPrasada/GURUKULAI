import 'package:flutter/material.dart';

class AppConstants {
  static const appName = 'Gurukul AI';
  static const appTagline = 'AI Tutor for Indian Competitive Exams';

  static const supportedExams = [
    'RRB NTPC', 'RRB ALP', 'RRB Group D', 'RRB Technician', 'RRB JE',
    'NDA', 'JEE', 'NEET',
  ];
  static const examKeys = [
    'rrb_ntpc', 'rrb_alp', 'rrb_group_d', 'rrb_technician', 'rrb_je',
    'nda', 'jee', 'neet',
  ];
  static const examDescriptions = [
    'Non-Technical Popular Categories',
    'Assistant Loco Pilot',
    'Group D — Level 1 Posts',
    'Technician — CBT 2 Pattern',
    'Junior Engineer — CBT 1 Pattern',
    'National Defence Academy',
    'Joint Entrance Examination',
    'National Eligibility cum Entrance Test',
  ];

  static const examsRequiringTrade = ['rrb_alp', 'rrb_technician'];
  static const examsRequiringDiscipline = ['rrb_je'];

  static const itiTrades = [
    'Electrician', 'Fitter', 'Machinist', 'Turner', 'Welder',
    'Electronics Mechanic', 'Mechanic Radio & TV', 'Heat Engine',
    'Wireman', 'Plumber', 'Carpenter', 'Painter (General)',
    'Mechanic Motor Vehicle', 'Tractor Mechanic', 'Diesel Mechanic',
    'Draughtsman (Civil)',
  ];

  static const engineeringDisciplines = [
    'Civil', 'Electrical', 'Mechanical', 'Electronics & Communication',
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
