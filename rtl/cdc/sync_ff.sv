// Synchronises c0_data_i into the capture_clk domain through Stages flops, all marked
// ASYNC_REG and powering up as zero. Latency is Stages capture_clk cycles, +/- 1 from
// metastability resolution.
// Each bit is synchronised independently: for Width > 1, the data must be Gray-coded or
// otherwise change one bit at a time, or the output can briefly show an incoherent mix.
// c0_data_i must come straight from a source-domain register (no combinational logic), and
// the path into the first stage needs a set_false_path or set_max_delay -datapath_only.
// No clk_en or rst, and no state struct: the chain must clock every cycle, and a plain
// array keeps the cell names (sync_reg_reg[*]) easy to match in constraints.
module sync_ff
#(
  parameter int Width = 1,
  parameter int Stages = 2,
  localparam int Latency = Stages
)
(
  input logic capture_clk,
  input logic [Width-1:0] c0_data_i,
  output logic [Width-1:0] cL_data_o
);

if(Width < 1) $error("Width must be >= 1 (got %0d)", Width);
if(Stages < 2) $error("Stages must be >= 2 (got %0d)", Stages);

(* ASYNC_REG = "TRUE" *) logic [Stages-1:0] [Width-1:0] sync_reg = '0;

assign cL_data_o = sync_reg[Stages-1];

always_ff @(posedge capture_clk) begin
  sync_reg[0] <= c0_data_i;
  for(int i = 0; i < Stages-1; i++) begin
    sync_reg[i+1] <= sync_reg[i];
  end
end

endmodule
