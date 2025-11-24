-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:05 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPVector)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
return {
    ["new"] = function(_, p_u_4, p_u_5, p_u_6, p_u_7, p_u_8, p_u_9, p_u_10, p_u_11, p12) --[[ Name: new ]] --[[ Line: 8 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_3 ]]
        local v15 = {
            ["get_t_for_distance_pct"] = function(p13, p14) --[[ Name: get_t_for_distance_pct ]] --[[ Line: 78 ]]
                return p13:get_t_for_distance(p13:get_distance() * p14);
            end
        }
        local v_u_16 = p12 == nil and 10 or p12
        local v_u_17 = {}
        local v_u_18 = 0
        v15.cons = function(_) --[[ Name: cons ]] --[[ Line: 16 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_4, (copy 3): p_u_5, (copy 4): v_u_17, (ref 5): v_u_16, (ref 6): v_u_1, (copy 7): p_u_6, (copy 8): p_u_7, (copy 9): p_u_8, (copy 10): p_u_9, (copy 11): p_u_10, (copy 12): p_u_11, (ref 13): v_u_18 ]]
            local v19 = 0
            local v20 = v_u_2:new(p_u_4, p_u_5)
            local v21 = v_u_2:new(0, 0)
            local v22 = v_u_2:new(0, 0)
            local v23 = 0
            v_u_17[#v_u_17 + 1] = {
                ["t"] = v19,
                ["distance"] = v23
            }
            for _ = 1, v_u_16 do
                v19 = v19 + 1 / v_u_16
                local v24 = v_u_1:BezierPt2ForT(p_u_4, p_u_5, p_u_6, p_u_7, p_u_8, p_u_9, p_u_10, p_u_11, v19)
                v21:set(v24.X, v24.Y)
                v22:set(v21._x - v20._x, v21._y - v20._y)
                v23 = v23 + v22:magnitude()
                v_u_17[#v_u_17 + 1] = {
                    ["t"] = v19,
                    ["distance"] = v23
                }
                v20:set(v21._x, v21._y)
            end;
            v_u_18 = v23
        end;
        v15.get_distance = function(_) --[[ Name: get_distance ]] --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            return v_u_18;
        end;
        local function f_t_to_dist_binsearch(p25) --[[ Name: t_to_dist_binsearch ]] --[[ Line: 43 ]]
            --[[ Upvalues: (copy 1): v_u_17, (ref 2): v_u_1 ]]
            local v26 = #v_u_17
            local v27 = 1
            while v26 - v27 > 1 do
                local v28 = math.floor((v_u_1:Lerp(v27, v26, 0.5)))
                if v_u_17[v28].distance < p25 then
                    v27 = v28
                    v28 = v26
                end;
                v26 = v28
            end;
            return v27;
        end;
        v15.get_t_for_distance = function(_, p29) --[[ Name: get_t_for_distance ]] --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_18, (copy 3): f_t_to_dist_binsearch, (copy 4): v_u_17, (ref 5): v_u_1 ]]
            local v30 = v_u_3:clamp(p29, 0, v_u_18)
            if v30 == v_u_18 then
                return 1;
            end;
            local v31 = f_t_to_dist_binsearch(v30)
            local v32 = v31 + 1
            local l_distance_0 = v_u_17[v31].distance
            return v_u_1:Lerp(v_u_17[v31].t, v_u_17[v32].t, (v30 - l_distance_0) / (v_u_17[v32].distance - l_distance_0));
        end;
        v15.get_y_for_distance_pct = function(p33, p34) --[[ Name: get_y_for_distance_pct ]] --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_4, (copy 3): p_u_5, (copy 4): p_u_6, (copy 5): p_u_7, (copy 6): p_u_8, (copy 7): p_u_9, (copy 8): p_u_10, (copy 9): p_u_11 ]]
            return v_u_1:BezierYForT(p_u_4, p_u_5, p_u_6, p_u_7, p_u_8, p_u_9, p_u_10, p_u_11, p33:get_t_for_distance_pct(p34));
        end;
        v15.to_string = function(_) --[[ Name: to_string ]] --[[ Line: 88 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): p_u_5, (copy 3): p_u_6, (copy 4): p_u_7, (copy 5): p_u_8, (copy 6): p_u_9, (copy 7): p_u_10, (copy 8): p_u_11 ]]
            return string.format("Bezier{(%.2f,%.2f),(%.2f,%.2f),(%.2f,%.2f),(%.2f,%.2f)}", p_u_4, p_u_5, p_u_6, p_u_7, p_u_8, p_u_9, p_u_10, p_u_11);
        end;
        v15:cons()
        return v15;
    end
};
