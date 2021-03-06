
session_viz = {}

session_viz.start = (data, elements) => {

    dataKeys = Object.keys(data)
    dataKeys.forEach(key => {
        var button = document.createElement("BUTTON");
        button.innerHTML = key;
        button.onclick = () => reload(data[key])
        document.getElementById("keys").appendChild(button)
    })


    function reload(data) {
        const code = data.codes

        node_color = group => (group === 1 && "#0000FF") || (group === 0 && "#00FF00") || "#FF0000"
        node_color_hid = group => (group === 1 && "#0000FF55") || (group === 0 && "#00FF0055") || "#FF000055"

        edge_color = group => (group === 1 && "#0000AA") || (group === 0 && "#00AA00") || "#AA0000"
        edge_color_hid = group => (group === 1 && "#0000AA55") || (group === 0 && "#00AA0055") || "#AA000055"


        var nodes = data.nodes.map(x => ({
            ...x,
            value: x.n,
            total: x.n,
            label: x.n.toString(),
            color: node_color(x.grp),
        }))//.slice(0,10)

        var edges = data.edges.map(x => ({
            ...x,
            from: x.source,
            to: x.target,
            arrows: "to",
            value: Math.pow(x.value, 2),
            total: x.value,
            color: edge_color((nodes[x.source] ?? {}).grp ?? 0),
        }))//.slice(0,10)

        var nodesDataset = new vis.DataSet(nodes);
        var edgesDataset = new vis.DataSet(edges);
        setInfo = (str) => document.getElementById('info').innerHTML = str

        highlightOnNode = (selected) => {
            edge_from_selected = edges.reduce((acc, { from, to }) => from === selected ? { [to]: true, ...acc } : acc, { [selected]: true })

            nodes = nodes.map((x, i) => ({
                ...x,
                color: i in edge_from_selected ? node_color(x.grp) : node_color_hid(x.grp),
            }))
            edges = edges.map(x => {
                group = (nodes[x.source] ?? {}).grp ?? 0
                return {
                    ...x,
                    color: x.source === selected ? edge_color(group) : edge_color_hid(group),
                }
            })

            const selected_node = nodes[selected]
            setInfo(`total: ${selected_node.total}\nast: ${selected_node.name}\n
---------------------\n\n${code[selected_node.name]}\n
---------------------\n\ndist to closest sat: ${(data.dists[selected_node.name]??{}).dist}\nsource of closest sat:\n${code[(data.dists[selected_node.name]??{}).ast]}
`)
            nodesDataset.update(nodes)
            edgesDataset.update(edges)
        }

        highlightOnEdge = (selected) => {
            const { from, to } = edges.find(({ id }) => id === selected)

            nodes = nodes.map((x, i) => ({
                ...x,
                color: i === from || i === to ? edge_color(x.grp) : edge_color_hid(x.grp),
            }))
            edges = edges.map(x => {
                group = (nodes[x.source] ?? {}).grp ?? 0
                return {
                    ...x,
                    color: x.id === selected ? edge_color(group) : edge_color_hid(group),
                }
            })

            const node_from = nodes[from]
            const node_to = nodes[to]
            const selected_edge = edges.find(x => x.id === selected)
            setInfo(`total: ${selected_edge.total}\n
--------------------------\nfrom:\nast: ${node_from.name}\n\n${code[node_from.name]}\n
--------------------------\nto:\nast: ${node_to.name}\n\n${code[node_to.name]}\n
                 `)
            nodesDataset.update(nodes)
            edgesDataset.update(edges)
        }

        highlightOff = () => {
            valid_nodes = nodes.filter(node => node.name !== "{true}" && node.grp !== 0 && data.dists[node.name])
            sum_dists = valid_nodes.reduce((acc, node) => acc + data.dists[node.name].dist * node.total,0)
            total_nodes = valid_nodes.reduce((acc, node) => acc + node.total,0)
            nodes = nodes.map(x => ({
                ...x,
                color: node_color(x.grp),
            }))
            edges = edges.map(x => ({
                ...x,
                color: edge_color((nodes[x.source] ?? {}).grp ?? 0),
            }))

            setInfo(`select a node or edge to show info.\n\n
total solved nodes: ${nodes.filter(node => node.grp === 0).reduce((acc, node) => acc + node.total, 0)}\n
stats not counting {true} or correct solutions:
    total nodes: ${total_nodes}\n
    sum of all distances: ${sum_dists}\n
    distance average: ${sum_dists/total_nodes}`)
            nodesDataset.update(nodes)
            edgesDataset.update(edges)
        }

        highlightHandler = (params) => {
            highlightOff(params)
            if (params.nodes.length > 0)
                highlightOnNode(params.nodes[0])
            else if (params.edges.length > 0)
                highlightOnEdge(params.edges[0])
        }

        draw = (nodes, edges) => {
            var container = document.getElementById('network');
            var data = {
                nodes: nodesDataset,
                edges: edgesDataset
            };
            var options = {
                nodes: {
                    shape: "dot"
                },
                physics: {
                    stabilization: false
                },
            }
            var network = new vis.Network(container, data, options);
            network.on("click", highlightHandler);
        }

        draw(nodes, edges)
    }

    reload(data[dataKeys[0]])
}
