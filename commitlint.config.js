// Conventional Commits, single-line only.
// House rules: NO commit body, NO footers (so no Co-Authored-By / "Generated with").
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'chore', 'docs', 'refactor', 'test', 'perf', 'build', 'ci'],
    ],
    'subject-case': [2, 'always', 'lower-case'],
    'subject-empty': [2, 'never'],
    'subject-full-stop': [2, 'never', '.'],
    'header-max-length': [2, 'always', 72],
    'body-max-line-length': [2, 'always', 0], // disallow a body
    'footer-max-line-length': [2, 'always', 0], // disallow footers/trailers
  },
};
