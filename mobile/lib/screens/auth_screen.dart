import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../widgets/common_widgets.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});
  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLogin = true;

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(32),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 400),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text('NOVA CORE', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Color(0xFF6366F1))),
                    const SizedBox(height: 8),
                    Text(_isLogin ? 'Sign in to your account' : 'Create an account', style: const TextStyle(color: Color(0xFF8888A8))),
                    const SizedBox(height: 32),
                    if (!_isLogin)
                      TextField(controller: _emailController, decoration: const InputDecoration(labelText: 'Name', hintText: 'Your name')),
                    const SizedBox(height: 16),
                    TextField(controller: _emailController, decoration: const InputDecoration(labelText: 'Email', hintText: 'you@example.com')),
                    const SizedBox(height: 16),
                    TextField(controller: _passwordController, obscureText: true, decoration: const InputDecoration(labelText: 'Password', hintText: 'Password')),
                    const SizedBox(height: 24),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: auth.isLoading ? null : () async {
                          final success = await auth.login(_emailController.text, _passwordController.text);
                          if (success && mounted) Navigator.of(context).pushReplacementNamed('/dashboard');
                        },
                        child: auth.isLoading ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2)) : Text(_isLogin ? 'Sign In' : 'Create Account'),
                      ),
                    ),
                    const SizedBox(height: 16),
                    TextButton(
                      onPressed: () => setState(() => _isLogin = !_isLogin),
                      child: Text(_isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in', style: const TextStyle(color: Color(0xFF6366F1))),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
