import sys

from tools.CodeRules.CodeRulesCli import CodeRulesCli

if __name__ == "__main__":
    sys.exit(CodeRulesCli.default().run(sys.argv[1:]))
