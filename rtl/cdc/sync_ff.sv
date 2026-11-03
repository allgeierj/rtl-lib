module sync_ff
#(
  parameter int Width = 1, // Incoherent for Width > 1
  parameter int Stages = 2,
  localparam int Latency = Stages
)
(
  input logic capture_clk, // capture clock
  input logic [Width-1:0] c0_data_i, // Should be driven from a reg
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
