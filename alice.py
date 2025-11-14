import logging
import garbler
import ot
import util
import utli_karol

class Alice(garbleryao.YaoGarbler):
    """Alice is the creator of the Yao circuit.

    Alice creates a Yao circuit and sends it to the evaluator along with her
    encrypted inputs. Alice will finally print the truth table of the circuit
    for all combination of Alice-Bob inputs.

    Alice does not know Bob's inputs but for the purpose
    of printing the truth table only, Alice assumes that Bob's inputs follow
    a specific order.

    Attributes:
        circuits: the JSON file containing circuits
        oblivious_transfer: Optional; enable the Oblivious Transfer protocol
            (True by default).
    """
    def __init__(self, circuits, oblivious_transfer=True, printmode="none", filename="", bitsize=4):
        super().__init__(circuits)
        self.socket = util.GarblerSocket()
        self.ot = ot.ObliviousTransfer(self.socket, enabled=oblivious_transfer)
        self.pm = printmode
        self.general_max = -1
        self.bitlen = bitsize
        if filename == "":
            _, self.private_value = utli_karol.private_func("Alice", bitsize=bitsize)
        else:
            _, self.private_value = utli_karol.private_func("Alice", bitsize=bitsize, file_read=True,
                                                            filename=filename)

    def start(self):
        """Start Yao protocol."""
        for circuit in self.circuits:
            to_send = {
                "circuit": circuit["circuit"],
                "garbled_tables": circuit["garbled_tables"],
                "pbits_out": circuit["pbits_out"],
            }
            logging.debug(f"Sending {circuit['circuit']['id']}")
            self.socket.send_wait(to_send)
            self.print(circuit)

    def print(self, entry):
        """Print circuit evaluation for all Bob and Alice inputs.

        Args:
            entry: A dict representing the circuit to evaluate.
        """
        circuit, pbits, keys = entry["circuit"], entry["pbits"], entry["keys"]
        outputs = circuit["out"]
        a_wires = circuit.get("alice", [])  # Alice's wires
        a_inputs = {}  # map from Alice's wires to (key, encr_bit) inputs
        b_wires = circuit.get("bob", [])  # Bob's wires
        b_keys = {  # map from Bob's wires to a pair (key, encr_bit)
            w: self._get_encr_bits(pbits[w], key0, key1)
            for w, (key0, key1) in keys.items() if w in b_wires
        }
        N = len(a_wires) + len(b_wires)

        print(f"======== {circuit['id']} ========")

        # Generate all inputs for both Alice and Bob
        for bits in [format(n, 'b').zfill(N) for n in range(2**N)]:
            bits_a = [int(b) for b in bits[:len(a_wires)]]  # Alice's inputs

            # Map Alice's wires to (key, encr_bit)
            for i in range(len(a_wires)):
                a_inputs[a_wires[i]] = (keys[a_wires[i]][bits_a[i]],
                                        pbits[a_wires[i]] ^ bits_a[i])

            # Send Alice's encrypted inputs and keys to Bob
            result = self.ot.get_result(a_inputs, b_keys)

            # Format output
            str_bits_a = ' '.join(bits[:len(a_wires)])
            str_bits_b = ' '.join(bits[len(a_wires):])
            str_result = ' '.join([str(result[w]) for w in outputs])

            print(f"  Alice{a_wires} = {str_bits_a} "
                  f"Bob{b_wires} = {str_bits_b}  "
                  f"Outputs{outputs} = {str_result}")

        print()

    def _get_encr_bits(self, pbit, key0, key1):
        return ((key0, 0 ^ pbit), (key1, 1 ^ pbit))
    
    def compute_response(self, input_data):
       
        circuit, pbits, key_pairs = input_data["circuit"], input_data["pbits"], input_data["key_pairs"]
        alice_wires = circuit.get("alice", [])  # Alice's wires
        alice_inputs = {}  # maps Alice's wires to (key, encrypted_bit) inputs
        bob_wires = circuit.get("bob", [])  # Bob's wires
        bob_keys = {  # maps Bob's wires to a pair (key, encrypted_bit)
            wire: self._get_encr_bits(pbits[wire], key0, key1)
            for wire, (key0, key1) in key_pairs.items() if wire in bob_wires
        }

        # Circuit input generated based on private value obtained during initialization
        alice_bits = [int(bit) for bit in self.private_value]  # Alice's inputs

        # Map Alice's wires to (key, encrypted_bit)
        for i in range(len(alice_wires)):
            alice_inputs[alice_wires[i]] = (key_pairs[alice_wires[i]][alice_bits[i]],
                                            pbits[alice_wires[i]] ^ alice_bits[i])

        # Send Alice's encrypted inputs and keys to Bob
        result = self.ot.get_result(alice_inputs, bob_keys)

        # Format output, save for further use, and print
        integer_result = utli_karol.circuit_output_to_int(result)
        self.general_max = integer_result
        print(f"Function result is {integer_result}")


