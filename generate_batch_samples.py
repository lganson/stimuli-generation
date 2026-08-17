"""
Batch generator for Figure-Ground Perception stimuli samples.
Generates images matching the three reference images and various experimental conditions
from Peterson & Salvagio (2008).

Run with: python3 generate_batch_samples.py
"""

from stimulus_generator import FigureGroundGenerator


def main():
    # # ── Matching Reference Image 1 ──────────────────────────────────────────
    # # ~7 visible edge curves, ~6-7 lobes, ~50% sub-lobes, probe at center-right
    # gen = FigureGroundGenerator(width=632, height=226, seed=101)
    # gen.generate(
    #     num_regions=8,
    #     num_lobes=7,
    #     fill_mode='outline',
    #     sublobe_prob=0.5,
    #     amplitude=24,
    #     probe_config={'enabled': True, 'region': 4, 'size': 14, 'color': 'red'},
    # ).save("match_ref1.png")
    # print("Saved match_ref1.png")
    #
    # # ── Matching Reference Image 2 ──────────────────────────────────────────
    # # ~5 curves, wider regions, ~8 lobes, sub-lobes visible, probe center
    # gen2 = FigureGroundGenerator(width=632, height=226, seed=102)
    # gen2.generate(
    #     num_regions=6,
    #     num_lobes=8,
    #     fill_mode='outline',
    #     sublobe_prob=0.5,
    #     amplitude=26,
    #     probe_config={'enabled': True, 'region': 3, 'size': 14, 'color': 'red'},
    #     seed=102
    # ).save("match_ref2.png")
    # print("Saved match_ref2.png")
    #
    # # ── Matching Reference Image 3 ──────────────────────────────────────────
    # # ~7 edges, more lobes (~10), sub-lobes, probe at center
    # gen3 = FigureGroundGenerator(width=632, height=226, seed=103)
    # gen3.generate(
    #     num_regions=8,
    #     num_lobes=10,
    #     fill_mode='outline',
    #     sublobe_prob=0.5,
    #     amplitude=24,
    #     probe_config={'enabled': True, 'region': 4, 'size': 14, 'color': 'red'},
    #     seed=103
    # ).save("match_ref3.png")
    # print("Saved match_ref3.png")

    # ── Experiment Conditions ───────────────────────────────────────────────

    # Exp 1: Binary Black & White alternating
    gen4 = FigureGroundGenerator(width=750, height=260)
    gen4.generate(
        num_regions=8,
        num_lobes=6,
        fill_mode='binary',
        sublobe_prob=0.44,
        amplitude=22,
        probe_config={'enabled': True, 'region': 4, 'size': 16, 'color': 'red'},
        spine_wobble=15
    ).save("exp1_binary_black_white.png")
    print("Saved exp1_binary_black_white.png")

    # Exp 2: Multicolored heterogeneous (each region different color)
    gen5 = FigureGroundGenerator(width=750, height=260)
    gen5.generate(
        num_regions=8,
        num_lobes=6,
        fill_mode='colored',
        convex_color_palette=['yellow', 'orange', 'green', 'blue'],
        concave_color_palette=['magenta', 'cyan', 'purple', 'pink'],
        sublobe_prob=0.44,
        amplitude=22,
        probe_config={'enabled': True, 'region': 4, 'size': 16, 'color': 'red'},
        spine_wobble=15

    ).save("exp2_multicolored_heterogeneous.png")
    print("Saved exp2_multicolored_heterogeneous.png")

    # Exp 3a: Homogeneous convex, heterogeneous concave
    gen6 = FigureGroundGenerator(width=750, height=260)
    gen6.generate(
        num_regions=8,
        num_lobes=6,
        fill_mode='homogeneous',
        target_part='convex',
        convex_color_palette=['gray'],
        concave_color_palette=['yellow', 'magenta', 'cyan', 'orange'],
        sublobe_prob=0.44,
        amplitude=22,
        probe_config={'enabled': True, 'region': 4, 'size': 16, 'color': 'red'},
        spine_wobble=15

    ).save("exp3a_homogeneous_convex.png")
    print("Saved exp3a_homogeneous_convex.png")

    # Exp 3b: Homogeneous concave, heterogeneous convex
    gen7 = FigureGroundGenerator(width=750, height=260)
    gen7.generate(
        num_regions=8,
        num_lobes=6,
        fill_mode='homogeneous',
        target_part='concave',
        concave_color_palette=['gray'],
        convex_color_palette=['yellow', 'magenta', 'cyan', 'orange'],
        sublobe_prob=0.44,
        amplitude=22,
        probe_config={'enabled': True, 'region': 4, 'size': 16, 'color': 'red'},
        spine_wobble=15

    ).save("exp3b_homogeneous_concave.png")
    print("Saved exp3b_homogeneous_concave.png")
    gen8 = FigureGroundGenerator(width=750, height=260)
    gen8.generate(
        num_regions=8,
        num_lobes=6,
        fill_mode='homogeneous',
        closure="closed",
        sublobe_prob=0.44,
        amplitude=22,
        spine_wobble=15.0
    ).save("exp5_homogeneous_closed.png")
    print("\nAll batch samples generated successfully!")


if __name__ == "__main__":
    main()
