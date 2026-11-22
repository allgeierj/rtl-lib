module fifo_async
#(
  parameter type DataType = logic [7:0],
  parameter int Depth = 512,
  parameter int SyncStages = 2,
  parameter RamStyle = "block",
  localparam int CountWidth = $clog2(Depth) + 1
)
(
  input logic wr_clk,
  input logic wr_rst = 1'b0,
  input logic wr_c0_valid_i,
  input DataType wr_c0_data_i,
  output logic wr_c0_ready_o,
  output logic [CountWidth-1:0] wr_c0_count_o,
  input logic rd_clk,
  input logic rd_rst = 1'b0,
  output logic rd_c0_valid_o,
  output DataType rd_c0_data_o,
  input logic rd_c0_ready_i,
  output logic [CountWidth-1:0] rd_c0_count_o
);

  if(Depth < 2 || (Depth & (Depth - 1)) != 0) $error("Depth must be a power of 2 >= 2 (got %0d)", Depth);
  if(SyncStages < 2) $error("SyncStages must be >= 2 (got %0d)", SyncStages);

endmodule
