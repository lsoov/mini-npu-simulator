import json
import time

EPSILON = 1e-9


def calculate_mac(pattern, filter_matrix):
    """외부 라이브러리 없이 이중 반복문으로 MAC(Multiply-Accumulate) 연산 수행"""
    n = len(pattern)
    total = 0.0
    for i in range(n):
        for j in range(n):
            total += pattern[i][j] * filter_matrix[i][j]
    return total


def measure_mac_time(pattern, filter_matrix, iterations=10):
    """I/O를 제외하고 순수 MAC 연산 함수 호출 시간만 반복 측정 (ms 단위 반환)"""
    start_time = time.perf_counter()
    for _ in range(iterations):
        calculate_mac(pattern, filter_matrix)
    end_time = time.perf_counter()
    avg_ms = ((end_time - start_time) / iterations) * 1000.0
    return avg_ms


def normalize_label(raw_label):
    """라벨 표준화: '+', 'cross' -> 'Cross' / 'x' -> 'X'"""
    if not isinstance(raw_label, str):
        return str(raw_label)
    cleaned = raw_label.strip().lower()
    if cleaned in ("+", "cross"):
        return "Cross"
    elif cleaned == "x":
        return "X"
    return raw_label


def validate_square_matrix(matrix, expected_size=None):
    """2차원 정사각 행렬 여부 및 크기 검증"""
    if not isinstance(matrix, list) or len(matrix) == 0:
        return False, "2차원 배열 형식이 아닙니다."
    n = len(matrix)
    if expected_size is not None and n != expected_size:
        return False, f"크기 불일치 (기대: {expected_size}x{expected_size}, 실제: {n}x{n})"
    for row in matrix:
        if not isinstance(row, list) or len(row) != n:
            return False, f"정사각 행렬이 아닙니다 (행 길이 불일치)."
        for val in row:
            if not isinstance(val, (int, float)):
                return False, "숫자가 아닌 값이 포함되어 있습니다."
    return True, ""


def input_3x3_matrix(name):
    """모드 1: 콘솔에서 3x3 행렬을 한 줄씩 입력받고 유효성 검증"""
    print(f"{name} (3줄 입력, 공백 구분)")
    matrix = []
    row_idx = 0
    while row_idx < 3:
        try:
            line = input().strip()
            parts = line.split()
            if len(parts) != 3:
                print("입력 형식 오류: 각 줄에 3개의 숫자를 공백으로 구분해 입력하세요.")
                continue
            row = [float(x) for x in parts]
            matrix.append(row)
            row_idx += 1
        except ValueError:
            print("입력 형식 오류: 숫자만 입력해야 합니다. 다시 입력하세요.")
    print()
    return matrix


def run_mode_1():
    """모드 1: 사용자 입력 (3x3) 실행 흐름"""
    print("\n#---------------------------------------")
    print("# [1] 필터 입력")
    print("#---------------------------------------")
    filter_a = input_3x3_matrix("필터 A")
    filter_b = input_3x3_matrix("필터 B")

    print("#---------------------------------------")
    print("# [2] 패턴 입력")
    print("#---------------------------------------")
    pattern = input_3x3_matrix("패턴")

    score_a = calculate_mac(pattern, filter_a)
    score_b = calculate_mac(pattern, filter_b)
    avg_time_ms = measure_mac_time(pattern, filter_a, iterations=10)

    print("#---------------------------------------")
    print("# [3] MAC 결과")
    print("#---------------------------------------")
    print(f"A 점수: {score_a:.16f}" if abs(score_a - score_b) < EPSILON else f"A 점수: {score_a}")
    print(f"B 점수: {score_b:.16f}" if abs(score_a - score_b) < EPSILON else f"B 점수: {score_b}")
    print(f"연산 시간(평균/10회): {avg_time_ms:.4f} ms")

    if abs(score_a - score_b) < EPSILON:
        print("판정: 판정 불가 (|A-B| < 1e-9)")
    elif score_a > score_b:
        print("판정: A")
    else:
        print("판정: B")

    print("\n#---------------------------------------")
    print("# [4] 성능 분석 (3×3)")
    print("#---------------------------------------")
    print(f"{'크기':<10} {'평균 시간(ms)':<15} {'연산 횟수'}")
    print("-" * 38)
    print(f"{'3×3':<10} {avg_time_ms:<15.4f} {9}")


def run_mode_2(filepath="data.json"):
    """모드 2: data.json 로드 및 일괄 분석 실행 흐름"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n[오류] '{filepath}' 파일을 찾을 수 없습니다. main.py와 같은 폴더에 위치시켜 주세요.")
        return
    except json.JSONDecodeError as e:
        print(f"\n[오류] JSON 파싱 실패: {e}")
        return

    raw_filters = data.get("filters", {})
    raw_patterns = data.get("patterns", {})

    print("\n#---------------------------------------")
    print("# [1] 필터 로드")
    print("#---------------------------------------")
    normalized_filters = {}
    for size_key, filter_dict in raw_filters.items():
        # size_5 -> 5 추출
        try:
            n = int(size_key.split("_")[1])
        except (IndexError, ValueError):
            print(f"✗ {size_key}: 잘못된 필터 크기 키 형식")
            continue

        normalized_filters[n] = {}
        loaded_labels = []
        for raw_label, matrix in filter_dict.items():
            std_label = normalize_label(raw_label)
            is_valid, err_msg = validate_square_matrix(matrix, expected_size=n)
            if is_valid:
                normalized_filters[n][std_label] = matrix
                loaded_labels.append(std_label)
            else:
                print(f"✗ {size_key} ({std_label}) 로드 오류: {err_msg}")

        if loaded_labels:
            print(f"✓ {size_key:<7} 필터 로드 완료 ({', '.join(loaded_labels)})")

    print("\n#---------------------------------------")
    print("# [2] 패턴 분석 (라벨 정규화 적용)")
    print("#---------------------------------------")

    total_tests = 0
    passed_tests = 0
    failed_cases = []
    perf_samples = {}  # 크기별 성능 측정을 위한 대표 샘플 저장

    # 성능 표에 3x3도 포함하기 위해 기본 3x3 샘플 준비
    sample_3x3_p = [[0.0, 1.0, 0.0], [1.0, 1.0, 1.0], [0.0, 1.0, 0.0]]
    sample_3x3_f = [[0.0, 1.0, 0.0], [1.0, 1.0, 1.0], [0.0, 1.0, 0.0]]
    perf_samples[3] = (sample_3x3_p, sample_3x3_f)

    for case_id, case_info in raw_patterns.items():
        total_tests += 1
        print(f"-- {case_id} ---")

        # 1) 키에서 N 추출 (예: size_5_1 -> 5)
        try:
            parts = case_id.split("_")
            n = int(parts[1])
        except (IndexError, ValueError):
            reason = "패턴 키에서 크기(N) 추출 실패"
            print(f"판정: FAIL ({reason})\n")
            failed_cases.append((case_id, reason))
            continue

        # 2) 해당 크기의 필터 존재 여부 확인
        if n not in normalized_filters or "Cross" not in normalized_filters[n] or "X" not in normalized_filters[n]:
            reason = f"size_{n}에 해당하는 Cross/X 필터가 없음"
            print(f"판정: FAIL ({reason})\n")
            failed_cases.append((case_id, reason))
            continue

        pattern_matrix = case_info.get("input")
        expected_raw = case_info.get("expected")
        expected_label = normalize_label(expected_raw)

        # 3) 패턴 행렬 크기 및 데이터 유효성 검증
        is_valid, err_msg = validate_square_matrix(pattern_matrix, expected_size=n)
        if not is_valid:
            reason = f"입력 패턴 스키마/크기 검증 실패 - {err_msg}"
            print(f"판정: FAIL ({reason})\n")
            failed_cases.append((case_id, reason))
            continue

        cross_filter = normalized_filters[n]["Cross"]
        x_filter = normalized_filters[n]["X"]

        # 성능 측정용 샘플 등록
        if n not in perf_samples:
            perf_samples[n] = (pattern_matrix, cross_filter)

        # 4) MAC 연산 및 점수 비교
        cross_score = calculate_mac(pattern_matrix, cross_filter)
        x_score = calculate_mac(pattern_matrix, x_filter)

        if abs(cross_score - x_score) < EPSILON:
            decision = "UNDECIDED"
        elif cross_score > x_score:
            decision = "Cross"
        else:
            decision = "X"

        # 동점일 때 부동소수점 차이를 눈으로 확인할 수 있도록 정밀 출력
        if decision == "UNDECIDED":
            print(f"Cross 점수: {cross_score:.16f}")
            print(f"X 점수: {x_score:.16f}")
        else:
            print(f"Cross 점수: {cross_score:.4f}")
            print(f"X 점수: {x_score:.4f}")

        if decision == expected_label:
            passed_tests += 1
            print(f"판정: {decision} | expected: {expected_label} | PASS\n")
        else:
            if decision == "UNDECIDED":
                reason = "동점(UNDECIDED) 처리 규칙(|Cross - X| < 1e-9)에 따라 FAIL"
            else:
                reason = f"예측 불일치 (판정: {decision}, 정답: {expected_label})"
            failed_cases.append((case_id, reason))
            print(f"판정: {decision} | expected: {expected_label} | FAIL ({reason})\n")

    print("#---------------------------------------")
    print("# [3] 성능 분석 (평균/10회)")
    print("#---------------------------------------")
    print(f"{'크기':<10} {'평균 시간(ms)':<15} {'연산 횟수'}")
    print("-" * 38)
    for n in sorted(perf_samples.keys()):
        p_mat, f_mat = perf_samples[n]
        avg_ms = measure_mac_time(p_mat, f_mat, iterations=10)
        ops = n * n
        size_str = f"{n}×{n}"
        print(f"{size_str:<10} {avg_ms:<15.4f} {ops}")

    print("\n#---------------------------------------")
    print("# [4] 결과 요약")
    print("#---------------------------------------")
    print(f"총 테스트: {total_tests}개")
    print(f"통과: {passed_tests}개")
    print(f"실패: {len(failed_cases)}개")

    if failed_cases:
        print("\n실패 케이스:")
        for cid, reason in failed_cases:
            print(f"- {cid}: {reason}")


def main():
    print("=== Mini NPU Simulator ===")
    print("[모드 선택]")
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")

    while True:
        choice = input("선택: ").strip()
        if choice == "1":
            run_mode_1()
            break
        elif choice == "2":
            run_mode_2("data.json")
            break
        else:
            print("잘못된 선택입니다. 1 또는 2를 입력하세요.")


if __name__ == "__main__":
    main()
    