import 'package:flutter/material.dart';
import 'constants.dart';

String formatDate(DateTime date) {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  return '${days[date.weekday - 1]}, ${date.day} ${months[date.month - 1]}';
}

String getExamDisplayName(String key) {
  final idx = AppConstants.examKeys.indexOf(key);
  return idx >= 0 ? AppConstants.supportedExams[idx] : key.toUpperCase();
}

Color scoreColor(double pct) {
  if (pct < 0.4) return const Color(0xFFE53935);
  if (pct < 0.6) return const Color(0xFFFF9800);
  return const Color(0xFF43A047);
}

String formatDuration(int minutes) {
  if (minutes < 60) return '${minutes}m';
  final h = minutes ~/ 60;
  final m = minutes % 60;
  return m == 0 ? '${h}h' : '${h}h ${m}m';
}

String truncateText(String text, int maxLen) {
  if (text.length <= maxLen) return text;
  return '${text.substring(0, maxLen)}...';
}

String scoreEmoji(double pct) {
  if (pct >= 0.8) return '🟢';
  if (pct >= 0.6) return '🟡';
  if (pct >= 0.4) return '🟠';
  return '🔴';
}
