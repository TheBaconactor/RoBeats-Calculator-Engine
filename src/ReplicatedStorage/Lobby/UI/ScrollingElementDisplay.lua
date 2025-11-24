-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:50 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
return {
    ["new"] = function(_, p_u_3, p_u_4) --[[ Name: new ]] --[[ Line: 6 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        local v5 = {}
        local v_u_6 = v_u_2:new()
        v5.cons = function(p7) --[[ Name: cons ]] --[[ Line: 11 ]]
            --[[ Upvalues: (copy 1): p_u_3 ]]
            p7:set_text(p_u_3.Text)
        end;
        v5.set_text = function(_, p8) --[[ Name: set_text ]] --[[ Line: 15 ]]
            --[[ Upvalues: (copy 1): v_u_6, (ref 2): v_u_1, (copy 3): p_u_3, (copy 4): p_u_4 ]]
            local v9 = #p8
            if v9 <= 0 then
                v9 = 1
            end;
            while v9 < 128 do
                p8 = p8 .. p8
                v9 = v9 * 2
            end;
            v_u_6:clear()
            local v10 = v_u_1:udim_obj_wrapper(p_u_3)
            v10._obj.Text = p8
            v10:set_pos(0, 0)
            v10:set_size(v10._obj.TextBounds.X, v10._obj.TextBounds.Y)
            v_u_6:push_back(v10)
            local v11 = v_u_1:udim_obj_wrapper(p_u_4)
            v11._obj.Text = p8
            v11:set_pos(v10:get_size().X + 5, 0)
            v11:set_size(v11._obj.TextBounds.X, v11._obj.TextBounds.Y)
            v_u_6:push_back(v11)
        end;
        v5.update = function(_, p12) --[[ Name: update ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): v_u_6 ]]
            for v13 = 1, v_u_6:count() do
                local v14 = v_u_6:get(v13)
                v14:set_pos(v14:get_pos().X - 0.25 * p12, v14:get_pos().Y)
            end;
            local v15 = v_u_6:get(1)
            local v16 = v_u_6:get(2)
            if v15:get_pos().X + v15:get_size().X < 0 then
                v15:set_size(v15._obj.TextBounds.X, v15._obj.TextBounds.Y)
                v15:set_pos(v16:get_pos().X + v16:get_size().X + 5, v15:get_pos().Y)
                v_u_6:push_back(v_u_6:pop_front())
            end;
        end;
        v5:cons()
        return v5;
    end
};
