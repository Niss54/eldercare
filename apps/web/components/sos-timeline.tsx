class Solution(object):
    def processStr(self, s, k):
        lengths = [0]

        for ch in s:
            cur = lengths[-1]

            if 'a' <= ch <= 'z':
                lengths.append(cur + 1)
            elif ch == '*':
                lengths.append(max(0, cur - 1))
            elif ch == '#':
                lengths.append(cur * 2)
            else:  # %
                lengths.append(cur)

        if k >= lengths[-1]:
            return '.'

        for i in range(len(s) - 1, -1, -1):
            ch = s[i]
            cur_len = lengths[i + 1]
            prev_len = lengths[i]

            if 'a' <= ch <= 'z':
                if k == prev_len:
                    return ch

            elif ch == '*':
                pass

            elif ch == '#':
                half = prev_len
                if k >= half:
                    k -= half

            else:  # %
                k = prev_len - 1 - k

        return '.'
