-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:01 PM
-- Cached decompilation

local v29 = {
    ["new"] = function(_, p1, p2, p3, p4) --[[ Name: new ]] --[[ Line: 3 ]]
        return {
            ["_x1"] = p1 == nil and 0 or p1,
            ["_y1"] = p2 == nil and 0 or p2,
            ["_x2"] = p3 == nil and 0 or p3,
            ["_y2"] = p4 == nil and 0 or p4,
            ["set"] = function(p5, p6, p7, p8, p9) --[[ Name: set ]] --[[ Line: 16 ]]
                p5._x1 = p6
                p5._y1 = p7
                p5._x2 = p8
                p5._y2 = p9
                return p5;
            end,
            ["set_centerxy_wid_hei"] = function(p10, p11, p12, p13, p14) --[[ Name: set_centerxy_wid_hei ]] --[[ Line: 24 ]]
                p10._x1 = p11 - p13 * 0.5
                p10._y1 = p12 - p14 * 0.5
                p10._x2 = p11 + p13 * 0.5
                p10._y2 = p12 + p14 * 0.5
            end,
            ["contains_xy"] = function(p15, p16, p17) --[[ Name: contains_xy ]] --[[ Line: 31 ]]
                local v18
                if p15._x1 <= p16 and (p16 <= p15._x2 and p15._y1 <= p17) then
                    v18 = p17 <= p15._y2
                else
                    v18 = false
                end;
                return v18;
            end,
            ["contains_vec2"] = function(p19, p20) --[[ Name: contains_vec2 ]] --[[ Line: 35 ]]
                return p19:contains_xy(p20.X, p20.Y);
            end,
            ["contains_rect"] = function(p21, p22) --[[ Name: contains_rect ]] --[[ Line: 39 ]]
                return p21._x1 <= p22._x2 and (p22._x1 <= p21._x2 and p21._y1 <= p22._y2) and p22._y1 <= p21._y2;
            end,
            ["get_nxy"] = function(p23, p24, p25) --[[ Name: get_nxy ]] --[[ Line: 47 ]]
                return (p23._x2 - p23._x1) * p24 + p23._x1, (p23._y2 - p23._y1) * p25 + p23._y1;
            end,
            ["to_string"] = function(p26) --[[ Name: to_string ]] --[[ Line: 51 ]]
                return string.format("{(%.2f,%.2f),(%.2f,%.2f)}", p26._x1, p26._y1, p26._x2, p26._y2);
            end,
            ["pt1"] = function(p27) --[[ Name: pt1 ]] --[[ Line: 55 ]]
                return Vector2.new(p27._x1, p27._y1);
            end,
            ["pt2"] = function(p28) --[[ Name: pt2 ]] --[[ Line: 56 ]]
                return Vector2.new(p28._x2, p28._y2);
            end
        };
    end,
    ["ZERO"] = v29:new(0, 0, 0, 0)
}
return v29;
