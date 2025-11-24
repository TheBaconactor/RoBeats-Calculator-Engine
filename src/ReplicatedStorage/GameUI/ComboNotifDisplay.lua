-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:29 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Shared.ChainCombo)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Local.DebugOut)
return {
    ["new"] = function(_, p_u_4, p_u_5, p_u_6, p_u_7, p_u_8, p9, p_u_10, p_u_11, p_u_12) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2 ]]
        local v13 = {}
        if p9 then
            p9.Visible = false
        end;
        local v_u_14 = 0
        local v_u_15 = 0
        local v_u_16 = 0
        local v_u_17 = 0
        local v_u_18 = 0
        local v_u_19 = 0
        v13.cons = function(_) --[[ Name: cons ]] --[[ Line: 43 ]]
            --[[ Upvalues: (copy 1): p_u_8, (copy 2): p_u_4, (copy 3): p_u_5, (copy 4): p_u_6, (copy 5): p_u_7 ]]
            p_u_8.TextTransparency = 1
            p_u_4.ImageTransparency = 1
            p_u_5.ImageTransparency = 1
            p_u_6.ImageTransparency = 1
            p_u_7.ImageTransparency = 1
        end;
        v13.update_alphas = function(_, p20, p21, p22, p23, p24) --[[ Name: update_alphas ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): p_u_8, (ref 3): v_u_1, (ref 4): v_u_16, (copy 5): p_u_4, (ref 6): v_u_17, (copy 7): p_u_5, (ref 8): v_u_18, (copy 9): p_u_6, (ref 10): v_u_19, (copy 11): p_u_7 ]]
            if v_u_15 ~= p20 then
                v_u_15 = p20
                p_u_8.TextTransparency = v_u_1:tra(v_u_15)
            end;
            if v_u_16 ~= p21 then
                v_u_16 = p21
                p_u_4.ImageTransparency = v_u_1:tra(v_u_16)
            end;
            if v_u_17 ~= p22 then
                v_u_17 = p22
                p_u_5.ImageTransparency = v_u_1:tra(v_u_17)
            end;
            if v_u_18 ~= p23 then
                v_u_18 = p23
                p_u_6.ImageTransparency = v_u_1:tra(v_u_18)
            end;
            if v_u_19 ~= p24 then
                v_u_19 = p24
                p_u_7.ImageTransparency = v_u_1:tra(v_u_19)
            end;
        end;
        v13.teardown = function(_) end;
        v13.update_with_chain_value = function(p25, p26, p27, _, p28) --[[ Name: update_with_chain_value ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_14, (copy 2): p_u_8, (ref 3): v_u_3, (copy 4): p_u_11, (copy 5): p_u_12, (ref 6): v_u_2, (ref 7): v_u_15, (ref 8): v_u_16, (ref 9): v_u_17, (ref 10): v_u_18, (ref 11): v_u_19, (copy 12): p_u_10 ]]
            local v29 = p28 == nil and 1 or p28
            if p27 ~= v_u_14 then
                p_u_8.Text = string.format("%d", p27)
            end;
            local v30 = 0
            local v31 = 0
            local v32 = 0
            local v33 = 0
            local v34 = 1
            if v29 <= 0.1 then
                v34 = 0
            else
                local v35 = v_u_3:notif_index(p27, p_u_11, p_u_12)
                if p27 == 0 then
                    v32 = 0
                    v30 = 0
                    v31 = 0
                    v33 = 0
                    v34 = 0
                elseif v35 == 4 then
                    v33 = 0.85
                elseif v35 == 3 then
                    v32 = 0.85
                elseif v35 == 2 then
                    v31 = 0.85
                else
                    v30 = 0.85
                end;
            end;
            local v36 = v_u_2:NormalizedDefaultExptValueInSeconds(0.45)
            p25:update_alphas(v_u_2:Expt(v_u_15, v34, v36, p26) * v29, v_u_2:Expt(v_u_16, v30, v36, p26) * v29, v_u_2:Expt(v_u_17, v31, v36, p26) * v29, v_u_2:Expt(v_u_18, v32, v36, p26) * v29, v_u_2:Expt(v_u_19, v33, v36, p26) * v29)
            local v37 = v_u_3:get_chain_target_scale(p27, p_u_11, p_u_12)
            if p27 ~= v_u_14 and p27 ~= 0 then
                if v_u_14 < p27 then
                    v37 = v37 * 2
                else
                    v37 = v37 * 0.5
                end;
            end;
            p_u_10:set_scale((v_u_2:Expt(p_u_10:get_scale(), v37, v_u_2:NormalizedDefaultExptValueInSeconds(0.45), p26)))
            p_u_10:layout()
            v_u_14 = p27
        end;
        v13:cons()
        return v13;
    end
};
