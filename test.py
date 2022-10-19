
from typing import Union, List
import argparse
import random
import matplotlib.pyplot as plt
# Q-Model class
class QModel:
    def __init__(self, c: int, K: int, Lambda: float, Mu: float) -> None:
        self.c = c
        self.K = K
        self.Lambda = Lambda
        self.Mu = Mu

        assert (
            Lambda < Mu * c
        ), f"lambda ({Lambda}) > c ({c}) x mu ({Mu}), which indicates the system can not keep steady"

        self.rho = Lambda / (c * Mu)
        self.P0 = self._compute_p0()

    def _compute_p0(self):
        rate = self.Lambda / self.Mu
        bias = rate ** self.c

        for i in range(1, self.c + 1):
            bias /= i

        bias /= 1 - self.rho
        p0 = 0

        temp1 = 1
        temp2 = 1
        for n in range(self.c):
            p0 += temp1 / temp2
            temp1 *= rate
            temp2 *= n + 1

        return 1 / (p0 + bias)

    def compute_lq(self):
        rate = self.Lambda / self.Mu
        lq = self.P0 * self.rho * (rate ** self.c) / ((1 - self.rho) ** 2)

        for i in range(1, self.c + 1):
            lq /= i

        return lq

    def compute_throughput_time(self):
        lq = self.compute_lq()
        wq = lq / self.Lambda
        w = wq + 1 / self.Mu

        return w

    def compute_number_of_jobs(self):
        lq = self.compute_lq()
        L = lq + self.Lambda / self.Mu

        return L


# Job-Flow class
class JobFlow:
    def __init__(self, mode: str, probs=None) -> None:
        """
        mode: `merge` or `split`
        """
        assert mode in [
            "merge",
            "split",
        ], f"The Job-Flow does not support `{mode}` mode!"

        self.mode = mode
        self.probs = probs

    def __call__(self, rates: Union[List[float], float]) -> Union[float, List[float]]:
        if self.mode == "merge":
            # merge
            return sum(rates)
        else:
            if isinstance(self.probs, int):
                self.probs = [1 / self.probs] * self.probs

            rates = [rates * prob for prob in self.probs]

            return rates


# Q-network class
class QNetwork:
    def __init__(
        self,
        n: int,
        m: int,
        Lambda: float,
        c: int,
        Mu: float,
        fail_rate=None,
    ) -> None:
        merge_gateway = JobFlow("merge")
        merged_lambda = merge_gateway([Lambda] * n)
        self.queue_models = []

        if fail_rate is None:
            distribute_gateway = JobFlow("split", m)
            lambdas = distribute_gateway(merged_lambda)

            for Lambda in lambdas:
                self.queue_models.append(QModel(c, -1, Lambda, Mu))
        else:
            # fail some processors randomly
            to_fail_num = int(c * m * fail_rate)
            marks = [1] * (c * m)

            to_fail_ids = list(range(c * m))
            random.shuffle(to_fail_ids)
            to_fail_ids = to_fail_ids[:to_fail_num]

            for idx in to_fail_ids:
                marks[idx] = 0

            processor_num = []
            for i in range(m):
                cur_processor_num = sum(marks[(c * i): (c * (i + 1))])
                if cur_processor_num:
                    processor_num.append(cur_processor_num)

            total = sum(processor_num)
            probs = [num / total for num in processor_num]
            distribute_gateway = JobFlow("split", probs)
            lambdas = distribute_gateway(merged_lambda)

            for idx, Lambda in enumerate(lambdas):
                self.queue_models.append(QModel(processor_num[idx], -1, Lambda, Mu))

    def compute_mean_throughput_time(self):
        throughtput_time = 0.0

        for qm in self.queue_models:
            throughtput_time = max(throughtput_time, qm.compute_throughput_time())

        return throughtput_time


def parse():
    parser = argparse.ArgumentParser("=== Simulator ===")

    parser.add_argument(
        "--input_flow_num", type=int, default=50, help="input flow number."
    )
    parser.add_argument("--Lambda", type=float, default=20, help="lambda")
    parser.add_argument("--cluster_num", type=int, help="cluster number")
    parser.add_argument("--server_num", type=int, help="server number in a cluster")
    parser.add_argument("--Mu", type=float, help="mu")
    parser.add_argument("--max_fail_rate", type=float, help="maximum failure rate")
    parser.add_argument("--repeat_times", type=int, help="repeat times")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse()

    # ======= Part 1 ======= #
    qnet = QNetwork(
        args.input_flow_num, args.cluster_num, args.Lambda, args.server_num, args.Mu
    )

    print(
        f"Mean throughout time: {format(qnet.compute_mean_throughput_time(), '.4f')} secs"
    )

    # ======= Part 2 ======= #
    random.seed(6223)

    fail_rates = []
    fail_rate = 0

    while fail_rate <= args.max_fail_rate:
        fail_rates.append(fail_rate)
        fail_rate += 0.04

    throughout_time = []
    for fail_rate in fail_rates:
        cur_throughout_time = []
        for repeat_time in range(args.repeat_times):
            qnet = QNetwork(
                args.input_flow_num,
                args.cluster_num,
                args.Lambda,
                args.server_num,
                args.Mu,
                fail_rate,
            )

            cur_throughout_time.append(qnet.compute_mean_throughput_time())

        throughout_time.append(sum(cur_throughout_time) / len(cur_throughout_time))

    fail_rates = [fail_rate * 100 for fail_rate in fail_rates]
    plt.plot(fail_rates, throughout_time)
    plt.xlabel("fail rate (%)")
    plt.ylabel("mean throughout time (secs)")
    plt.show()

#It can be seen from the generated results and figures:
#The mean throughput time for the first processor network was 0.0667 seconds. And the increase rate of mean throughput time is basically balanced.
#The mean throughput time for the second processor network was 0.0500 seconds.When the failure rate reaches 16%, the increase rate of mean throughput time becomes larger.
