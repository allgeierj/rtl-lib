module gray2bin_tb
#(
  parameter int Width = 8
)
(
  input  logic [Width-1:0] c0_gray_i,
  output logic [Width-1:0] c0_bin_o
);

gray2bin #(.Width(Width))
u_gray2bin (.c0_gray_i, .c0_bin_o);

endmodule
