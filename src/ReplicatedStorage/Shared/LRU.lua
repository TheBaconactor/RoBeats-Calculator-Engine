-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:07 PM
-- Cached decompilation

return {
    ["new"] = function(p_u_1, p_u_2) --[[ Name: new ]] --[[ Line: 7 ]]
        assert(p_u_1 >= 1, "max_size must be >= 1")
        assert(not p_u_2 or p_u_2 >= 1, "max_bytes must be >= 1")
        local v_u_3 = 0
        local v_u_4 = 0
        local v_u_5 = {}
        local v_u_6 = nil
        local v_u_7 = nil
        local v_u_8 = nil
        local function _(p9) --[[ Name: cut ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_6 ]]
            local v10 = p9[2]
            local v11 = p9[3]
            p9[2] = nil
            p9[3] = nil
            if v10 and v11 then
                v10[3] = v11
                v11[2] = v10
                return;
            elseif v10 then
                v10[3] = nil
                v_u_7 = v10
                return;
            elseif v11 then
                v11[2] = nil
                v_u_6 = v11
            else
                v_u_6 = nil
                v_u_7 = nil
            end;
        end;
        local function _(p12) --[[ Name: setNewest ]] --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7 ]]
            if v_u_6 then
                p12[3] = v_u_6
                v_u_6[2] = p12
                v_u_6 = p12
            else
                v_u_6 = p12
                v_u_7 = p12
            end;
        end;
        local function _(p13, p14) --[[ Name: del ]] --[[ Line: 71 ]]
            --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_7, (ref 3): v_u_6, (ref 4): v_u_3, (ref 5): v_u_4, (ref 6): v_u_8 ]]
            v_u_5[p13] = nil
            local v15 = p14[2]
            local v16 = p14[3]
            p14[2] = nil
            p14[3] = nil
            if v15 and v16 then
                v15[3] = v16
                v16[2] = v15
            elseif v15 then
                v15[3] = nil
                v_u_7 = v15
            elseif v16 then
                v16[2] = nil
                v_u_6 = v16
            else
                v_u_6 = nil
                v_u_7 = nil
            end;
            v_u_3 = v_u_3 - 1
            v_u_4 = v_u_4 - (p14[5] or 0)
            v_u_8 = p14
        end;
        local function f_makeFreeSpace(p17) --[[ Name: makeFreeSpace ]] --[[ Line: 81 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_1, (copy 3): p_u_2, (ref 4): v_u_4, (ref 5): v_u_7, (copy 6): v_u_5, (ref 7): v_u_6, (ref 8): v_u_8 ]]
            while p_u_1 < v_u_3 + 1 or p_u_2 and p_u_2 < v_u_4 + p17 do
                assert(v_u_7, "not enough storage for cache")
                local v18 = v_u_7
                v_u_5[v_u_7[4]] = nil
                local v19 = v18[2]
                local v20 = v18[3]
                v18[2] = nil
                v18[3] = nil
                if v19 and v20 then
                    v19[3] = v20
                    v20[2] = v19
                elseif v19 then
                    v19[3] = nil
                    v_u_7 = v19
                elseif v20 then
                    v20[2] = nil
                    v_u_6 = v20
                else
                    v_u_6 = nil
                    v_u_7 = nil
                end;
                v_u_3 = v_u_3 - 1
                v_u_4 = v_u_4 - (v18[5] or 0)
                v_u_8 = v18
            end;
        end;
        local function f_set(_, p21, p22, p23) --[[ Name: set ]] --[[ Line: 100 ]]
            --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_7, (ref 3): v_u_6, (ref 4): v_u_3, (ref 5): v_u_4, (ref 6): v_u_8, (copy 7): p_u_2, (copy 8): f_makeFreeSpace ]]
            local v24 = v_u_5[p21]
            if v24 then
                v_u_5[p21] = nil
                local v25 = v24[2]
                local v26 = v24[3]
                v24[2] = nil
                v24[3] = nil
                if v25 and v26 then
                    v25[3] = v26
                    v26[2] = v25
                elseif v25 then
                    v25[3] = nil
                    v_u_7 = v25
                elseif v26 then
                    v26[2] = nil
                    v_u_6 = v26
                else
                    v_u_6 = nil
                    v_u_7 = nil
                end;
                v_u_3 = v_u_3 - 1
                v_u_4 = v_u_4 - (v24[5] or 0)
                v_u_8 = v24
            end;
            if p22 == nil then
                assert(p21 ~= nil, "Key may not be nil")
            else
                local v27 = p_u_2 and (p23 or (#p22 or 0)) or 0
                f_makeFreeSpace(v27)
                local v28 = v_u_8 or {}
                v_u_5[p21] = v28
                v28[1] = p22
                v28[4] = p21
                v28[5] = p_u_2 and v27
                v_u_3 = v_u_3 + 1
                v_u_4 = v_u_4 + v27
                if v_u_6 then
                    v28[3] = v_u_6
                    v_u_6[2] = v28
                    v_u_6 = v28
                else
                    v_u_6 = v28
                    v_u_7 = v28
                end;
            end;
            v_u_8 = nil
        end;
        local function f_mynext(_, p29) --[[ Name: mynext ]] --[[ Line: 127 ]]
            --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_6 ]]
            local v30
            if p29 then
                v30 = v_u_5[p29][3]
            else
                v30 = v_u_6
            end;
            if v30 then
                return v30[4], v30[1];
            else
                return nil;
            end;
        end;
        local function f_lru_pairs() --[[ Name: lru_pairs ]] --[[ Line: 142 ]]
            --[[ Upvalues: (copy 1): f_mynext ]]
            return f_mynext, nil, nil;
        end;
        return setmetatable({}, {
            ["__index"] = {
                ["get"] = function(_, p31) --[[ Name: get ]] --[[ Line: 90 ]]
                    --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_7, (ref 3): v_u_6 ]]
                    local v32 = v_u_5[p31]
                    if not v32 then
                        return nil;
                    end;
                    local v33 = v32[2]
                    local v34 = v32[3]
                    v32[2] = nil
                    v32[3] = nil
                    if v33 and v34 then
                        v33[3] = v34
                        v34[2] = v33
                    elseif v33 then
                        v33[3] = nil
                        v_u_7 = v33
                    elseif v34 then
                        v34[2] = nil
                        v_u_6 = v34
                    else
                        v_u_6 = nil
                        v_u_7 = nil
                    end;
                    if v_u_6 then
                        v32[3] = v_u_6
                        v_u_6[2] = v32
                        v_u_6 = v32
                    else
                        v_u_6 = v32
                        v_u_7 = v32
                    end;
                    return v32[1];
                end,
                ["set"] = f_set,
                ["delete"] = function(p35, p36) --[[ Name: delete ]] --[[ Line: 123 ]]
                    --[[ Upvalues: (copy 1): f_set ]]
                    return f_set(p35, p36, nil);
                end,
                ["pairs"] = f_lru_pairs
            },
            ["__pairs"] = f_lru_pairs
        });
    end
};
